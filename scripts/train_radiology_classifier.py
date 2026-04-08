from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
MPL_CONFIG_DIR = BACKEND_ROOT / ".matplotlib"
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import joblib
import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import LinearSVC

matplotlib.use("Agg")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.radiology_classifier import (  # noqa: E402
    MODEL_PATH,
    SentenceEmbeddingVectorizer,
    preprocess_report_text,
)
from prepare_dataset import DEFAULT_OUTPUT_PATH, DEFAULT_REPORTS_DIR, prepare_dataset  # noqa: E402


@dataclass
class ExperimentConfig:
    name: str
    vectorizer_factory: Callable[[], Any]
    classifier_factory: Callable[[], Any]
    ngram_range: tuple[int, int] | None = None
    optional_dependency: str | None = None
    requires_label_encoding: bool = False
    input_mode: str = "preprocessed"
    explain_vectorizer_factory: Callable[[], Any] | None = None
    explain_classifier_factory: Callable[[], Any] | None = None


@dataclass
class ExperimentResult:
    name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    classification_report_text: str
    confusion_labels: list[str]
    confusion_matrix_values: np.ndarray
    vectorizer: Any
    classifier: Any
    explain_vectorizer: Any | None
    explain_classifier: Any | None
    label_encoder: LabelEncoder | None
    notes: str = ""
    skipped: bool = False


def dependency_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def load_dataset_rows(dataset_path: Path) -> tuple[list[str], list[str], list[str]]:
    import csv

    raw_texts: list[str] = []
    texts: list[str] = []
    labels: list[str] = []
    with dataset_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            report_text = (row.get("report_text") or "").strip()
            disease_label = (row.get("disease_label") or "").strip()
            if not report_text or not disease_label:
                continue
            raw_texts.append(report_text)
            texts.append(preprocess_report_text(report_text))
            labels.append(disease_label)
    return raw_texts, texts, labels


def format_confusion_matrix(labels: list[str], matrix: np.ndarray) -> str:
    cell_width = max(12, max(len(label) for label in labels) + 2)
    header = " " * cell_width + "".join(f"{label:>{cell_width}}" for label in labels)
    rows = [header]
    for label, row in zip(labels, matrix.tolist(), strict=False):
        rows.append(f"{label:>{cell_width}}" + "".join(f"{value:>{cell_width}d}" for value in row))
    return "\n".join(rows)


def save_confusion_matrix_plot(
    labels: list[str],
    matrix: np.ndarray,
    output_path: Path,
    model_name: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig_width = max(8, len(labels) * 0.9)
    fig_height = max(6, len(labels) * 0.75)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    image = ax.imshow(matrix, cmap="Blues")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

    ax.set_title(f"Confusion Matrix: {model_name}")
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)

    max_value = int(matrix.max()) if matrix.size else 0
    threshold = max_value / 2 if max_value else 0
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = int(matrix[row_index, col_index])
            text_color = "white" if value > threshold else "black"
            ax.text(col_index, row_index, str(value), ha="center", va="center", color=text_color)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def build_base_experiments() -> list[ExperimentConfig]:
    return [
        ExperimentConfig(
            name="TF-IDF + Logistic Regression",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.98,
                max_features=12000,
                sublinear_tf=True,
            ),
            classifier_factory=lambda: LogisticRegression(
                max_iter=3000,
                class_weight="balanced",
                C=1.5,
            ),
            ngram_range=(1, 2),
        ),
        ExperimentConfig(
            name="TF-IDF + LinearSVM",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.98,
                max_features=12000,
                sublinear_tf=True,
            ),
            classifier_factory=lambda: CalibratedClassifierCV(
                LinearSVC(C=1.25, class_weight="balanced"),
                cv=3,
            ),
            explain_classifier_factory=lambda: LinearSVC(C=1.25, class_weight="balanced"),
            ngram_range=(1, 2),
        ),
        ExperimentConfig(
            name="TF-IDF FeatureUnion + LinearSVM",
            vectorizer_factory=lambda: FeatureUnion(
                [
                    (
                        "word",
                        TfidfVectorizer(
                            ngram_range=(1, 3),
                            min_df=1,
                            max_df=0.995,
                            max_features=25000,
                            sublinear_tf=True,
                        ),
                    ),
                    (
                        "char",
                        TfidfVectorizer(
                            analyzer="char_wb",
                            ngram_range=(4, 6),
                            min_df=2,
                            max_features=25000,
                            sublinear_tf=True,
                        ),
                    ),
                ]
            ),
            classifier_factory=lambda: LinearSVC(C=1.5, class_weight="balanced"),
            explain_vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.995,
                max_features=25000,
                sublinear_tf=True,
            ),
            explain_classifier_factory=lambda: LinearSVC(C=1.5, class_weight="balanced"),
            ngram_range=(1, 3),
        ),
        ExperimentConfig(
            name="TF-IDF + RandomForest",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.98,
                max_features=8000,
                sublinear_tf=True,
            ),
            classifier_factory=lambda: RandomForestClassifier(
                n_estimators=350,
                max_depth=None,
                min_samples_leaf=1,
                class_weight="balanced_subsample",
                n_jobs=1,
                random_state=42,
            ),
            ngram_range=(1, 2),
        ),
        ExperimentConfig(
            name="TF-IDF + XGBoost",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.98,
                max_features=15000,
                sublinear_tf=True,
            ),
            classifier_factory=_make_xgboost_classifier,
            optional_dependency="xgboost",
            requires_label_encoding=True,
            ngram_range=(1, 2),
        ),
        ExperimentConfig(
            name="Sentence Transformers + Logistic Regression",
            vectorizer_factory=lambda: SentenceEmbeddingVectorizer("all-MiniLM-L6-v2"),
            classifier_factory=lambda: LogisticRegression(
                max_iter=4000,
                class_weight="balanced",
                C=2.0,
            ),
            optional_dependency="sentence_transformers",
            input_mode="raw",
        ),
    ]


def build_tuned_experiments() -> list[ExperimentConfig]:
    return [
        ExperimentConfig(
            name="TF-IDF + Logistic Regression (Tuned)",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.99,
                max_features=20000,
                sublinear_tf=True,
            ),
            classifier_factory=lambda: LogisticRegression(
                max_iter=4000,
                class_weight="balanced",
                C=3.0,
            ),
            ngram_range=(1, 3),
        ),
        ExperimentConfig(
            name="TF-IDF + LinearSVM (Tuned)",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.99,
                max_features=20000,
                sublinear_tf=True,
            ),
            classifier_factory=lambda: CalibratedClassifierCV(
                LinearSVC(C=1.75, class_weight="balanced"),
                cv=3,
            ),
            explain_classifier_factory=lambda: LinearSVC(C=1.75, class_weight="balanced"),
            ngram_range=(1, 3),
        ),
        ExperimentConfig(
            name="TF-IDF FeatureUnion + LinearSVM (Tuned)",
            vectorizer_factory=lambda: FeatureUnion(
                [
                    (
                        "word",
                        TfidfVectorizer(
                            ngram_range=(1, 3),
                            min_df=1,
                            max_df=0.995,
                            max_features=30000,
                            sublinear_tf=True,
                        ),
                    ),
                    (
                        "char",
                        TfidfVectorizer(
                            analyzer="char_wb",
                            ngram_range=(4, 6),
                            min_df=2,
                            max_features=30000,
                            sublinear_tf=True,
                        ),
                    ),
                ]
            ),
            classifier_factory=lambda: LinearSVC(C=1.5, class_weight="balanced"),
            explain_vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.995,
                max_features=30000,
                sublinear_tf=True,
            ),
            explain_classifier_factory=lambda: LinearSVC(C=1.5, class_weight="balanced"),
            ngram_range=(1, 3),
        ),
        ExperimentConfig(
            name="TF-IDF + RandomForest (Tuned)",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.99,
                max_features=12000,
                sublinear_tf=True,
            ),
            classifier_factory=lambda: RandomForestClassifier(
                n_estimators=500,
                max_depth=None,
                min_samples_leaf=1,
                class_weight="balanced_subsample",
                n_jobs=1,
                random_state=42,
            ),
            ngram_range=(1, 3),
        ),
        ExperimentConfig(
            name="TF-IDF + XGBoost (Tuned)",
            vectorizer_factory=lambda: TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.99,
                max_features=20000,
                sublinear_tf=True,
            ),
            classifier_factory=lambda: _make_xgboost_classifier(
                n_estimators=450,
                max_depth=6,
                learning_rate=0.04,
            ),
            optional_dependency="xgboost",
            requires_label_encoding=True,
            ngram_range=(1, 3),
        ),
    ]


def _make_xgboost_classifier(
    *,
    n_estimators: int = 300,
    max_depth: int = 5,
    learning_rate: float = 0.05,
):
    from xgboost import XGBClassifier  # type: ignore

    return XGBClassifier(
        objective="multi:softprob",
        eval_metric="mlogloss",
        tree_method="hist",
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=4,
    )


def run_experiment(
    config: ExperimentConfig,
    train_inputs: dict[str, list[str]],
    test_inputs: dict[str, list[str]],
    y_train: list[str],
    y_test: list[str],
) -> ExperimentResult:
    if config.optional_dependency and not dependency_available(config.optional_dependency):
        return ExperimentResult(
            name=config.name,
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1=0.0,
            classification_report_text="",
            confusion_labels=[],
            confusion_matrix_values=np.zeros((0, 0), dtype=int),
            vectorizer=None,
            classifier=None,
            explain_vectorizer=None,
            explain_classifier=None,
            label_encoder=None,
            notes=f"Skipped because '{config.optional_dependency}' is not installed.",
            skipped=True,
        )

    try:
        train_texts = train_inputs[config.input_mode]
        test_texts = test_inputs[config.input_mode]
        vectorizer = config.vectorizer_factory()
        classifier = config.classifier_factory()
        explain_vectorizer = config.explain_vectorizer_factory() if config.explain_vectorizer_factory else None
        explain_classifier = config.explain_classifier_factory() if config.explain_classifier_factory else None

        X_train = (
            vectorizer.fit_transform(train_texts, y_train)
            if hasattr(vectorizer, "fit_transform")
            else vectorizer.fit(train_texts, y_train).transform(train_texts)
        )
        X_test = vectorizer.transform(test_texts)

        label_encoder: LabelEncoder | None = None
        y_train_fit: list[str] | np.ndarray = y_train
        if config.requires_label_encoding:
            label_encoder = LabelEncoder()
            label_encoder.fit(y_train)
            y_train_fit = label_encoder.transform(y_train)

        classifier.fit(X_train, y_train_fit)

        if explain_vectorizer is not None and explain_classifier is not None:
            X_train_explain = (
                explain_vectorizer.fit_transform(train_texts, y_train)
                if hasattr(explain_vectorizer, "fit_transform")
                else explain_vectorizer.fit(train_texts, y_train).transform(train_texts)
            )
            explain_classifier.fit(X_train_explain, y_train_fit)
        elif explain_classifier is not None:
            explain_vectorizer = vectorizer
            explain_classifier.fit(X_train, y_train_fit)

        predicted = classifier.predict(X_test)
        if label_encoder is not None:
            predicted = label_encoder.inverse_transform(np.asarray(predicted, dtype=int))

        labels_sorted = sorted(set(y_train) | set(y_test))
        accuracy = float(accuracy_score(y_test, predicted))
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test,
            predicted,
            average="weighted",
            zero_division=0,
        )
        matrix = confusion_matrix(y_test, predicted, labels=labels_sorted)
        report = classification_report(
            y_test,
            predicted,
            labels=labels_sorted,
            zero_division=0,
        )

        return ExperimentResult(
            name=config.name,
            accuracy=accuracy,
            precision=float(precision),
            recall=float(recall),
            f1=float(f1),
            classification_report_text=report,
            confusion_labels=labels_sorted,
            confusion_matrix_values=matrix,
            vectorizer=vectorizer,
            classifier=classifier,
            explain_vectorizer=explain_vectorizer,
            explain_classifier=explain_classifier,
            label_encoder=label_encoder,
            notes="",
        )
    except Exception as exc:
        return ExperimentResult(
            name=config.name,
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1=0.0,
            classification_report_text="",
            confusion_labels=[],
            confusion_matrix_values=np.zeros((0, 0), dtype=int),
            vectorizer=None,
            classifier=None,
            explain_vectorizer=None,
            explain_classifier=None,
            label_encoder=None,
            notes=f"Failed during training: {exc}",
            skipped=True,
        )


def print_result(result: ExperimentResult) -> None:
    print(f"Model: {result.name}")
    if result.skipped:
        print(f"Status: {result.notes}")
        print()
        return

    print(f"Accuracy: {result.accuracy:.3f}")
    print(f"Precision: {result.precision:.3f}")
    print(f"Recall: {result.recall:.3f}")
    print(f"F1: {result.f1:.3f}")
    print("Classification Report:")
    print(result.classification_report_text)
    print("Confusion Matrix:")
    print(format_confusion_matrix(result.confusion_labels, result.confusion_matrix_values))
    print()


def better_result(candidate: ExperimentResult, current: ExperimentResult | None) -> bool:
    if candidate.skipped:
        return False
    if current is None:
        return True
    if candidate.accuracy != current.accuracy:
        return candidate.accuracy > current.accuracy
    if candidate.f1 != current.f1:
        return candidate.f1 > current.f1
    return candidate.precision > current.precision


def save_best_model(result: ExperimentResult, output_path: Path, dataset_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_name": result.name,
        "vectorizer": result.vectorizer,
        "classifier": result.classifier,
        "explain_vectorizer": result.explain_vectorizer,
        "explain_classifier": result.explain_classifier,
        "label_encoder": result.label_encoder,
        "metrics": {
            "accuracy": round(result.accuracy, 4),
            "precision": round(result.precision, 4),
            "recall": round(result.recall, 4),
            "f1_score": round(result.f1, 4),
        },
        "classes": result.confusion_labels,
        "confusion_matrix": {
            "labels": result.confusion_labels,
            "matrix": result.confusion_matrix_values.tolist(),
        },
        "dataset_path": str(dataset_path),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "preprocessing": {
            "strategy": "lowercase + punctuation removal + stopword filtering + simple lemmatization",
            "dataset_curation": "single-label reports only; ambiguous multi-label reports are excluded before training",
            "notes": "Trainer uses preprocessed report text for TF-IDF experiments and raw text for optional sentence embeddings. Safety-critical runtime rules remain active for sparse labels.",
        },
    }
    joblib.dump(bundle, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the Radion AI radiology classifier.")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help="Directory containing XML reports.",
    )
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Prepared dataset CSV path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=MODEL_PATH,
        help="Trained model output path.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=50,
        help="Minimum samples per class retained in the prepared dataset.",
    )
    parser.add_argument(
        "--target-accuracy",
        type=float,
        default=0.95,
        help="Minimum target accuracy before stopping experimentation.",
    )
    parser.add_argument(
        "--plot-output",
        type=Path,
        default=PROJECT_ROOT / "backend" / "models" / "radiology_classifier_confusion_matrix.png",
        help="Path to save the matplotlib confusion matrix image for the best model.",
    )
    args = parser.parse_args()

    _, raw_counts, filtered_counts = prepare_dataset(
        args.reports_dir,
        args.dataset_path,
        min_samples=args.min_samples,
    )
    raw_texts, texts, labels = load_dataset_rows(args.dataset_path)
    if not texts:
        raise RuntimeError(f"No training rows were prepared in {args.dataset_path}")

    train_raw_texts, test_raw_texts, train_texts, test_texts, y_train, y_test = train_test_split(
        raw_texts,
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    train_inputs = {
        "raw": train_raw_texts,
        "preprocessed": train_texts,
    }
    test_inputs = {
        "raw": test_raw_texts,
        "preprocessed": test_texts,
    }

    all_results: list[ExperimentResult] = []
    best_result: ExperimentResult | None = None

    for config in build_base_experiments():
        result = run_experiment(config, train_inputs, test_inputs, y_train, y_test)
        all_results.append(result)
        print_result(result)
        if better_result(result, best_result):
            best_result = result

    if best_result and best_result.accuracy < args.target_accuracy:
        print(
            f"Best accuracy {best_result.accuracy:.3f} is below target {args.target_accuracy:.3f}. "
            "Running tuned experiments.\n"
        )
        for config in build_tuned_experiments():
            result = run_experiment(config, train_inputs, test_inputs, y_train, y_test)
            all_results.append(result)
            print_result(result)
            if better_result(result, best_result):
                best_result = result

    if best_result is None or best_result.skipped:
        raise RuntimeError("No trainable model was produced.")

    save_best_model(best_result, args.output, args.dataset_path)
    save_confusion_matrix_plot(
        best_result.confusion_labels,
        best_result.confusion_matrix_values,
        args.plot_output,
        best_result.name,
    )

    summary = {
        "dataset_path": str(args.dataset_path),
        "output_path": str(args.output),
        "plot_output_path": str(args.plot_output),
        "raw_label_counts": raw_counts,
        "filtered_label_counts": filtered_counts,
        "best_model": best_result.name,
        "accuracy": round(best_result.accuracy, 4),
        "precision": round(best_result.precision, 4),
        "recall": round(best_result.recall, 4),
        "f1": round(best_result.f1, 4),
    }
    print(json.dumps(summary, indent=2))
    return 0 if best_result.accuracy >= args.target_accuracy else 1


if __name__ == "__main__":
    raise SystemExit(main())
