BioRED Relations Baseline v1

Run ID:
20260528_165825_exp

Model Path:
outputs/baselines/biored_relations_v1/model

Report Path:
outputs/baselines/biored_relations_v1/report

Metrics (from test_metrics.json):
- eval_f1_macro: 0.5687177594154339
- eval_f1_micro: 0.7662116040955631
- eval_loss: 1.817969799041748

Label Set:
- Association
- Correlation
- No_Relation

Key Config:
- pair_mode: gene_disease
- correlation_merge_mode: merged
- negative_ratio: 2
- class_weight_mode: balanced
- num_train_epochs: 5

Notes:
- This baseline freezes the first stable 3-class relation model.
- Use this directory as comparison target for future experiments.

True Test Metrics: (on June.15th)
- eval_f1_macro: 0.5762780398575141
- eval_f1_micro: 0.7440677966101695
- eval_loss: 2.092841625213623
