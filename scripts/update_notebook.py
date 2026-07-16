import json

notebook_path = "colab_finetuning_pipeline.ipynb"

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Update instructions
instructions_cell = nb['cells'][0]
for i, line in enumerate(instructions_cell['source']):
    if "Upload your `dataset.jsonl`" in line:
        instructions_cell['source'][i] = line.replace("dataset.jsonl", "refined_dataset.jsonl")

# Update data loader cell
loader_cell = nb['cells'][3]
new_source = [
    "from unsloth.chat_templates import get_chat_template\n",
    "tokenizer = get_chat_template(\n",
    "    tokenizer,\n",
    "    chat_template = \"llama-3\",\n",
    "    mapping = {\"role\" : \"role\", \"content\" : \"content\", \"user\" : \"user\", \"assistant\" : \"model\"},\n",
    ")\n",
    "\n",
    "def formatting_prompts_func(examples):\n",
    "    convos = examples[\"messages\"]\n",
    "    texts = [tokenizer.apply_chat_template(convo, tokenize = False, add_generation_prompt = False) for convo in convos]\n",
    "    return { \"text\" : texts, }\n",
    "\n",
    "from datasets import load_dataset\n",
    "\n",
    "print(\"Loading refined_dataset.jsonl...\")\n",
    "dataset = load_dataset(\"json\", data_files=\"refined_dataset.jsonl\", split=\"train\")\n",
    "dataset = dataset.map(formatting_prompts_func, batched = True,)\n"
]

loader_cell['source'] = new_source

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Successfully updated notebook.")
