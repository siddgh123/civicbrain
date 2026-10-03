"""Complaint-text classifier training (docs/06_AI_PIPELINE.md sec. 2.2, training/train_text_clf.py).

Trains on the committed CSVs in data/complaints (no model file needed, so this also runs in CI).
"""

import pytest

from training import train_text_clf as tc

CATEGORIES = ["Blocked Drain", "Garbage Accumulation", "Other", "Pothole", "Road Damage", "Streetlight", "Water Leakage", "Waterlogging"]


@pytest.fixture(scope="module")
def data():
    return tc.load_data()


@pytest.fixture(scope="module")
def trained(data):
    return tc.train(data)


def test_training_data_follows_the_recipe(data):
    assert [f.rows for f in data.train_files] == [500, 160]
    assert len(data.train_texts) == len(data.train_labels) == 660
    # synthetic rows are title + ". " + description
    assert data.train_texts[0] == "Road repair required. Damaged portion of road requires maintenance."
    assert len(data.sanity_texts) == 40
    assert sorted(set(data.train_labels)) == sorted(set(data.sanity_labels)) == CATEGORIES


def test_pipeline_matches_the_recipe():
    pipe = tc.build_pipeline(5.0)
    features = dict(pipe.named_steps["features"].transformer_list)
    assert features["word"].analyzer == "word" and features["word"].ngram_range == (1, 2) and features["word"].sublinear_tf
    assert features["char"].analyzer == "char_wb" and features["char"].ngram_range == (2, 5) and features["char"].sublinear_tf
    clf = pipe.named_steps["clf"]
    assert (clf.C, clf.class_weight, clf.max_iter, clf.random_state) == (5.0, "balanced", 2000, 42)


def test_c_is_chosen_by_cross_validation_over_the_grid(trained):
    assert set(trained.cv_mean_by_c) == {1.0, 2.0, 5.0, 10.0}
    best = max(trained.cv_mean_by_c.values())
    # ties go to the smallest C (stronger regularisation), like GridSearchCV
    assert trained.c == min(c for c, m in trained.cv_mean_by_c.items() if m == best)


def test_training_is_deterministic(data, trained):
    again = tc.train(data)
    assert again.c == trained.c
    assert list(again.pipeline.predict(data.sanity_texts)) == list(trained.pipeline.predict(data.sanity_texts))
    assert (again.pipeline.predict_proba(data.sanity_texts) == trained.pipeline.predict_proba(data.sanity_texts)).all()


def test_sanity_metrics_are_recorded_and_guarded(data, trained):
    m = tc.evaluate(trained.pipeline, data.sanity_texts, data.sanity_labels)
    assert m["rows"] == 40
    assert m["labels"] == CATEGORIES
    assert len(m["confusion_matrix"]) == 8 and sum(map(sum, m["confusion_matrix"])) == 40
    assert 0 <= m["macro_f1"] <= 1
    # regression guard (measured ~0.90 with this recipe, docs/06 sec. 2.2)
    assert m["accuracy"] >= tc.SANITY_MIN_ACCURACY == 0.80


def test_metrics_document_is_labelled_honestly(data, trained):
    doc = tc.metrics_document(data, trained, tc.evaluate(trained.pipeline, data.sanity_texts, data.sanity_labels), sha256="ab" * 32)
    assert doc["sanity"]["label"] == "sanity check on 40 kit-written sentences"
    assert doc["kind"] == "text-classifier"
    assert doc["model_sha256"] == "ab" * 32
    assert [f["rows"] for f in doc["train"]["files"]] == [500, 160]
    assert all(len(f["sha256"]) == 64 for f in doc["train"]["files"])


def test_manifest_entry_names_data_c_and_metrics(data, trained):
    metrics = tc.evaluate(trained.pipeline, data.sanity_texts, data.sanity_labels)
    entry = tc.manifest_entry(data, trained, metrics, sha256="cd" * 32)
    assert entry["path"] == "text_clf.joblib"
    assert entry["kind"] == "text-classifier"
    assert entry["sha256"] == "cd" * 32 and entry["version"] == ("cd" * 32)[:12]
    assert entry["C"] == trained.c
    assert [(f["file"], f["rows"]) for f in entry["data"]] == [
        ("data/complaints/synthetic_complaints_500.csv", 500),
        ("data/complaints/kit_authored_train.csv", 160),
    ]
    assert entry["metrics"]["sanity_accuracy"] == metrics["accuracy"]
    assert entry["metrics_file"] == "text_clf_metrics.json"
