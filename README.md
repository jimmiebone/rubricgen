# rubricgen

**把评分标准写成机器能查的规则。**

`rubricgen` —— 把自然语言评分标准拆成可机械判定的检查项，并标出仍需人判断的部分。

- 零依赖，Python 3.10+ 标准库即可运行
- 单文件，`rubricgen.py` 拷走就能用
- 不联网、不写文件

<!-- ipos:install -->
## 安装

零依赖，Python 3.10+ 即可：

```bash
pip install jimmiebone-rubricgen
```

装完直接用命令名调用：

```bash
rubricgen --help
```

也可以不用安装，直接把 `rubricgen.py` 拷走用——它只依赖标准库。

## 为什么需要它

评分标准工具多只做模板；rubricgen 明确区分「能机器判定」与「必须人判断」，不假装全自动。

它遵守下面几条自己定的规矩：

1. **诚实地区分**。能机械判定的和必须人读的，明确分开，不假装全自动——假装全自动的评分系统比没有评分更危险。
2. **规则要能落地**。每条机器规则都得说清：检查什么、什么算通过。
3. **不评价标准本身好不好**，只负责把它变成可执行的检查。

## 用法

```bash
python rubricgen.py --file rubric.md
python rubricgen.py --file rubric.md --json
```

加 `--json` 可以拿到机器可读的结果，便于接到流水线里。

## 已知局限

- 机器可判定与否靠关键词信号，判断不了「这条标准该怎么执行」。
- 生成的是规则骨架，不是可直接跑的断言代码。
- 不评价标准本身合不合理。

## 跑测试

```bash
python test_rubricgen.py
```

测试用独立的断言与临时数据，不污染工作目录。

## 来源与参考

- Python 标准库文档：<https://docs.python.org/3/>
- GitHub 仓库：<https://github.com/jimmiebone/rubricgen>

---

## 关于作者

jimmiebone 做评分标准的可判定化相关的问题。这个工具先替你回答一个具体问题，再谈别的。

- 个人主页：<https://jimmiebone.github.io>
- 仓库：<https://github.com/jimmiebone/rubricgen>

## 许可

MIT，见 [LICENSE](LICENSE)。
