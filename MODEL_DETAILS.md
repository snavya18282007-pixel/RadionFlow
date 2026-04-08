# Radiology Model Details

## Current Runtime Model

The currently saved and loaded classifier is:

- Model name: `TF-IDF FeatureUnion + LinearSVM`
- Model artifact: `backend/app/models/radiology_classifier.pkl`
- Reported metrics:
  - Accuracy: `0.9712`
  - Precision: `0.9712`
  - Recall: `0.9712`
  - F1 Score: `0.9704`

This metadata is loaded at runtime from the trained model bundle used by the backend service.

## Overall Pipeline

The system is a hybrid of:

1. ML-based text classification
2. Rule-based clinical safety checks

The final prediction flow is:

1. Extract report text from radiology records
2. Normalize and preprocess the text
3. Convert the text into numerical features
4. Run the trained classifier
5. Apply runtime safety rules for critical findings
6. Return the final label, confidence, and top keywords

## How The Data Is Extracted

Training data preparation is implemented in `scripts/prepare_dataset.py`.

The dataset builder:

- reads XML radiology reports from `data/reports`
- extracts the `FINDINGS` and `IMPRESSION` sections
- extracts MeSH terms when available
- assigns labels using a combination of:
  - MeSH term pattern matching
  - text pattern matching
  - negation filtering

Examples of negation-aware logic:

- `no pneumonia` should not be labeled as pneumonia
- `without pleural effusion` should not be labeled as pleural effusion

Only single-label reports are kept for training. Ambiguous or multi-label cases are excluded to keep the training set cleaner.

## Labels Predicted By The Model

The classification target labels are normalized into these categories:

- `normal`
- `cardiomegaly`
- `pleural_effusion`
- `pneumonia`
- `tuberculosis`
- `lung_cancer`
- `other_lung_abnormality`

## Text Preprocessing

Text preprocessing is implemented in `backend/app/services/radiology_classifier.py`.

The preprocessing steps include:

- lowercasing the report text
- removing punctuation and extra whitespace
- removing common stopwords and radiology boilerplate words
- simple rule-based lemmatization
- tokenization into normalized terms

This produces a cleaned representation of the report before feature extraction.

## Feature Extraction

The currently deployed model uses `TF-IDF FeatureUnion`.

It combines two vectorizers:

1. Word-level TF-IDF
   - uses word n-grams from 1 to 3
   - captures phrases such as `pleural effusion` or `airspace opacity`

2. Character-level TF-IDF
   - uses character n-grams with `char_wb`
   - captures subword patterns and helps with spelling variation and short phrase structure

This combination gives the classifier both phrase-level and character-pattern information.

## Classification Algorithm

The currently deployed model uses:

- `LinearSVC` from scikit-learn

This is a linear Support Vector Machine classifier.

At inference time:

1. The report is converted into TF-IDF feature vectors
2. `LinearSVC` predicts the most likely class
3. Confidence is derived from model scores in the runtime prediction code

Because SVM does not naturally provide probabilities in the same way as logistic regression, the service uses decision scores and converts them into a probability-like distribution when needed.

## Other Algorithms Supported During Training

The training script in `scripts/train_radiology_classifier.py` evaluates multiple candidate models:

- `TF-IDF + Logistic Regression`
- `TF-IDF + LinearSVM`
- `TF-IDF FeatureUnion + LinearSVM`
- `TF-IDF + RandomForest`
- `TF-IDF + XGBoost`
- `Sentence Transformers + Logistic Regression`

If the best initial model does not meet the target accuracy, the script also runs tuned versions of several models.

## Runtime Safety Rules

The backend includes rule-based clinical safeguards in `backend/app/services/radiology_classifier.py`.

These rules look for strong disease-indicative phrases such as:

- `active tuberculosis`
- `spiculated mass`
- `bronchogenic carcinoma`
- `lobar consolidation`
- `cardiomegaly`
- `pleural effusion`

Negation-aware checks are applied so that phrases like `no evidence of pneumonia` are not treated as positive findings.

The runtime rules are especially important for high-risk categories such as:

- `tuberculosis`
- `lung_cancer`

If the rule-based evidence is strong enough, it can override or strengthen the ML prediction for safety reasons.

## Explainability / Keyword Extraction

The system also returns top keywords that help explain the prediction.

Keyword extraction works as follows:

- for linear models, it uses model coefficients (`coef_`)
- for tree-based models, it uses feature importance values (`feature_importances_`)
- if model-based explanation is unavailable, it falls back to extracting candidate keywords from the report text

This helps surface phrases that most influenced the classification result.

## Summary

The deployed solution is not just a plain classifier. It is a hybrid diagnostic text pipeline that combines:

- structured training data preparation
- TF-IDF based text feature extraction
- a Linear SVM classifier
- runtime rule-based safety overrides
- lightweight explainability through extracted keywords

This design is useful for radiology triage because it balances:

- strong text classification performance
- interpretability
- safety handling for critical disease patterns
