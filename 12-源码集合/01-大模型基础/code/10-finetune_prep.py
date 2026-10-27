from datasets import Dataset
import json

def prepare_sft_data(raw_data_path):
    """准备 SFT 训练数据"""
    with open(raw_data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    formatted_data = []
    for item in raw_data:
        formatted_data.append({
            "messages": [
                {"role": "user", "content": item["question"]},
                {"role": "assistant", "content": item["answer"]}
            ]
        })
    
    dataset = Dataset.from_list(formatted_data)
    dataset = dataset.train_test_split(test_size=0.2, seed=42)
    train_val = dataset["train"].train_test_split(test_size=0.125, seed=42)
    
    return {
        "train": train_val["train"],
        "eval": train_val["test"],
        "test": dataset["test"]
    }

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

def train_lora(model_name, train_dataset, eval_dataset, output_dir):
    """LoRA + SFT 训练"""
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # 4-bit 量化配置（降低显存占用）
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="bfloat16",
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # LoRA 配置
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
        task_type="CAUSAL_LM",
    )
    
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,
        load_best_model_at_end=True,
        fp16=False,
        bf16=True,
        report_to="wandb",
    )
    
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=training_args,
        max_seq_length=1024,
        dataset_text_field="messages",
        tokenizer=tokenizer,
    )
    
    trainer.train()
    trainer.save_model(output_dir)
    return trainer

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def load_finetuned_model(base_model_name, lora_path):
    """加载微调后的模型"""
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name, device_map="auto", trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(base_model, lora_path)
    model.eval()
    return model, tokenizer

def generate_response(model, tokenizer, prompt, max_new_tokens=512):
    """生成回答"""
    messages = [{"role": "user", "content": prompt}]
    input_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs, max_new_tokens=max_new_tokens,
            temperature=0.7, top_p=0.9, do_sample=True,
        )
    
    response = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
    )
    return response

class FineTuningValidator:
    """微调模型验证器"""
    
    def __init__(self, base_model, finetuned_model, tokenizer, test_set):
        self.base_model = base_model
        self.ft_model = finetuned_model
        self.tokenizer = tokenizer
        self.test_set = test_set
    
    def evaluate_single(self, prompt, expected, model):
        """评估单个样本"""
        response = generate_response(model, self.tokenizer, prompt)
        score = self.compute_score(response, expected)
        return score, response
    
    def compute_score(self, response, expected):
        """计算得分"""
        return 1.0 if self.check_match(response, expected) else 0.0
    
    def check_match(self, response, expected):
        """简单的匹配检查"""
        expected_keywords = expected.split()[:5]
        matched = sum(1 for kw in expected_keywords if kw in response)
        return matched >= len(expected_keywords) * 0.6
    
    def run_comparison(self):
        """对比基线模型和微调模型"""
        results = {
            "total": len(self.test_set),
            "base_passed": 0,
            "finetuned_passed": 0,
            "improved": 0,
            "regressed": 0,
            "details": []
        }
        
        for case in self.test_set:
            base_score, base_response = self.evaluate_single(
                case["prompt"], case["expected"], self.base_model
            )
            ft_score, ft_response = self.evaluate_single(
                case["prompt"], case["expected"], self.ft_model
            )
            
            base_ok = base_score >= 0.6
            ft_ok = ft_score >= 0.6
            
            if base_ok:
                results["base_passed"] += 1
            if ft_ok:
                results["finetuned_passed"] += 1
            if not base_ok and ft_ok:
                results["improved"] += 1
            if base_ok and not ft_ok:
                results["regressed"] += 1
            
            results["details"].append({
                "prompt": case["prompt"][:50],
                "base_ok": base_ok,
                "finetuned_ok": ft_ok,
            })
        
        results["base_accuracy"] = results["base_passed"] / results["total"]
        results["finetuned_accuracy"] = results["finetuned_passed"] / results["total"]
        results["improvement_rate"] = results["improved"] / results["total"]
        results["regression_rate"] = results["regressed"] / results["total"]
        return results

def test_finetuned_model_regression():
    """微调模型回归测试"""
    validator = FineTuningValidator(
        base_model=load_model("qwen2.5-7b"),
        finetuned_model=load_model("qwen2.5-7b-my-finetune"),
        tokenizer=load_tokenizer("qwen2.5-7b"),
        test_set=load_test_set("comprehensive_test.json")
    )

    results = validator.run_comparison()

    # 微调必须有效
    assert results["finetuned_accuracy"] > results["base_accuracy"], \
        f"微调未提升: {results['finetuned_accuracy']:.2%} vs {results['base_accuracy']:.2%}"

    # 不能灾难性遗忘
    assert results["regression_rate"] < 0.05, \
        f"遗忘严重: {results['regression_rate']:.2%} 通用任务退步"

    # 领域任务提升幅度
    assert results["improvement_rate"] > 0.2, \
        f"提升不足: 仅 {results['improvement_rate']:.2%} 从失败变成功"

    print(f"微调验证通过！")
    print(f"  基线准确率: {results['base_accuracy']:.2%}")
    print(f"  微调准确率: {results['finetuned_accuracy']:.2%}")
    print(f"  提升率: {results['improvement_rate']:.2%}")
    print(f"  遗忘率: {results['regression_rate']:.2%}")

# 在 TrainingArguments 中添加
training_args = TrainingArguments(
    gradient_checkpointing=True,  # 梯度检查点
    fp16=False,
    bf16=True,
    ...
)

results = validator.run_comparison()
print(f"领域提升: +{results['improvement_rate']:.0%}")
print(f"通用遗忘: {results['regression_rate']:.0%}")
print(f"基线准确率: {results['base_accuracy']:.0%}")
print(f"微调准确率: {results['finetuned_accuracy']:.0%}")
