# Label Guide: `label_id` vs `entity_type`

## What `label_id` Exactly Means

`label_id` is the model's predicted class index (an integer).

- The model produces logits for each token.
- `argmax(logits)` selects one class index.
- That selected index is `label_id`.

So `label_id` is only a numeric code, not a biological meaning by itself.
You must convert it with `id2label`:

- `label_id` -> `label_name` (for example `4 -> I-Chemical`)

## Why You See Numbers

The model predicts class IDs internally (for example `0`, `1`, `2`).
These are stored as `label_id`.

`label_id` is only an index. It is not a biological meaning by itself.

## What You Should Read in Analysis

- Use `entity_type` (for example `Disease`, `Chemical`, `Gene`) for interpretation.
- Use `label_id` only for debugging/model validation.

## BIO Label Format

Most token labels follow BIO tagging:

- `B-XXX`: beginning of an entity
- `I-XXX`: inside/continuation of an entity
- `O`: outside any entity

In this project, typical `XXX` values are:

- `Disease`: disease entity
- `Chemical`: chemical/drug entity

So common labels are:

- `B-Disease`: first token of a disease mention
- `I-Disease`: continuation token of that same disease mention
- `B-Chemical`: first token of a chemical mention
- `I-Chemical`: continuation token of that same chemical mention

Example:

- Token labels: `B-Disease I-Disease O B-Chemical`
- Entity output:
  - `Disease` span
  - `Chemical` span

## Concrete Example of ID Mapping

Example mapping (varies by trained model):

- `0 -> O`
- `1 -> B-Chemical`
- `2 -> I-Chemical`
- `3 -> B-Disease`
- `4 -> I-Disease`

If a token gets `label_id = 4`, it means this token is mapped to `I-Disease`
for that model.

## Where Mapping Comes From

The mapping is saved in model config during training:

- `id2label`: number -> label name
- `label2id`: label name -> number

The app now shows this mapping table on the page under:

- **Label Mapping (`label_id` ↔ `label_name`)**
