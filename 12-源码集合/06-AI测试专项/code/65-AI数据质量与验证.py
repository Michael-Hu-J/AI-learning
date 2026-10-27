from ydata_profiling import ProfileReport

# 一行代码生成数据概览报告
profile = ProfileReport(df, title="数据质量报告", explorative=True)
profile.to_file("data_quality_report.html")

import great_expectations as gx

# 创建验证期望
expectations = [
    {"expect_column_values_to_not_be_null": {"column": "user_id"}},
    {"expect_column_values_to_be_between": {"column": "age", "min_value": 0, "max_value": 120}},
    {"expect_column_values_to_be_in_set": {"column": "gender", "value_set": ["男", "女", "其他"]}},
    {"expect_column_values_to_match_regex": {"column": "email", "regex": r"^[^@]+@[^@]+\.[^@]+$"}},
]

class DataQualityChecker:
    def __init__(self, df):
        self.df = df
        self.issues = []
    
    def check_all(self):
        """一键检查所有质量维度"""
        results = {}
        results['完整性'] = self._check_completeness()
        results['准确性'] = self._check_accuracy()
        results['一致性'] = self._check_consistency()
        results['唯一性'] = self._check_uniqueness()
        results['分布分析'] = self._analyze_distribution()
        return results
    
    def _check_completeness(self):
        """检查缺失值"""
        missing = self.df.isnull().sum()
        missing_pct = missing / len(self.df) * 100
        critical = missing_pct[missing_pct > 20]
        if len(critical) > 0:
            self.issues.append(f"⚠️ 严重缺失: {dict(critical)}")
        return {"缺失统计": missing.to_dict(), "缺失率%": missing_pct.to_dict()}
    
    def _check_accuracy(self):
        """检查异常值（IQR方法）"""
        numeric_cols = self.df.select_dtypes(include='number').columns
        outliers = {}
        for col in numeric_cols:
            Q1, Q3 = self.df[col].quantile([0.25, 0.75])
            IQR = Q3 - Q1
            outlier_mask = (self.df[col] < Q1 - 1.5*IQR) | (self.df[col] > Q3 + 1.5*IQR)
            count = outlier_mask.sum()
            if count > 0:
                outliers[col] = int(count)
        return {"异常值数量": outliers}
    
    def _check_consistency(self):
        """检查枚举值一致性"""
        issues = {}
        for col in self.df.select_dtypes(include='object').columns:
            unique_vals = self.df[col].unique()
            # 检查大小写不一致
            lower_vals = [str(v).lower().strip() for v in unique_vals if pd.notna(v)]
            if len(lower_vals) != len(set(lower_vals)):
                issues[col] = f"发现大小写不一致的值"
        return issues
    
    def _check_uniqueness(self):
        """检查重复数据"""
        dup_rows = self.df.duplicated().sum()
        return {"重复行数": int(dup_rows), "重复率%": round(dup_rows/len(self.df)*100, 2)}
    
    def _analyze_distribution(self):
        """分析类别分布"""
        cat_cols = self.df.select_dtypes(include=['object', 'category']).columns
        dist = {}
        for col in cat_cols:
            vc = self.df[col].value_counts()
            top_pct = vc.iloc[0] / len(self.df) * 100
            dist[col] = {
                "类别数": len(vc),
                "最大类别占比%": round(top_pct, 2),
                "是否不平衡": top_pct > 80
            }
        return dist

checker = DataQualityChecker(df)
results = checker.check_all()
for issue in checker.issues:
    print(issue)

def build_cleaning_pipeline(df, config):
    """
    构建数据清洗流水线
    config: 清洗配置字典
    """
    steps = []
    
    if config.get('remove_duplicates'):
        steps.append(lambda d: d.drop_duplicates())
    
    if config.get('handle_missing'):
        steps.append(lambda d: fill_missing(d, config.get('missing_strategy', 'median')))
    
    if config.get('remove_outliers'):
        steps.append(lambda d: clip_outliers(d, method='iqr'))
    
    if config.get('standardize_text'):
        steps.append(lambda d: standardize_text_columns(d))
    
    # 按顺序执行
    cleaned = df.copy()
    for step in steps:
        before = len(cleaned)
        cleaned = step(cleaned)
        after = len(cleaned)
        print(f"清洗步骤: 行数 {before} → {after}")
    
    return cleaned

import schedule
import time

def daily_quality_check():
    """每日数据质量检查"""
    df = load_latest_data()  # 加载最新数据
    checker = DataQualityChecker(df)
    results = checker.check_all()
    
    # 检查是否触发告警
    if results['完整性']['缺失率%'].get('关键字段', 0) > 10:
        send_alert("⚠️ 关键字段缺失率超过10%")
    
    if results['唯一性']['重复率%'] > 5:
        send_alert("⚠️ 数据重复率超过5%")
    
    # 记录质量分数趋势
    record_quality_score(calculate_score(results))

# 每天凌晨2点执行
schedule.every().day.at("02:00").do(daily_quality_check)
