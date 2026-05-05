# 附录代码清单建议

以下文件建议作为比赛论文附录中的核心代码提交，覆盖数据抓取配置、数据清洗、文本分析、主题建模与情感分析五个关键环节。

## 1. 抓取配置文件

- `config/base_config.py`
- 作用：展示关键词设置、抓取平台、并发控制、休眠时间、评论抓取等核心采集参数。

## 2. 数据清洗与结构化导出

- `tools/clean_xhs_to_excel.py`
- 作用：将原始 CSV 清洗为 Excel，完成去空值、去重、去 URL、去表情等预处理。

## 3. 高频词、词云、共现网络、情感分布

- `tools/analyze_xhs_comments.py`
- 作用：基于 `comments_clean` 完成分词、停用词过滤、Top 高频词统计、词云图、共现网络图、情感直方图生成。

## 4. 情感极性分类与负面样本提取

- `tools/sentiment_pie_xhs_comments.py`
- 作用：将评论划分为正面、中性、负面三类，生成情感饼图，并输出负面代表性评论。

## 5. LDA 主题模型与可视化

- `tools/lda_xhs_comments.py`
- 作用：基于清洗后评论文本构建 LDA 主题模型，自动在 3 到 4 个主题间选优，导出主题词并生成 `lda_visualization.html`。

## 推荐提交方式

建议附录正文只放以上 5 个文件。

如果篇幅有限，优先保留以下 3 个文件：

- `tools/clean_xhs_to_excel.py`
- `tools/analyze_xhs_comments.py`
- `tools/lda_xhs_comments.py`

这三份代码基本已经能完整体现你的研究技术路线：数据清洗 -> 文本特征提取 -> 主题建模。