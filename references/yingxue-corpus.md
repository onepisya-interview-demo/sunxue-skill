<!--
Source: bayshier/sunxue
Original path: yingxue/references/corpus.md
Original license: MIT
Copyright (c) 2026 bayshier
来源仓库: https://github.com/bayshier/sunxue (v1.4.0,main 分支 2026-08-28 commit,无 v1.4.0 tag)
原内容用途: 曾颖(@zengying1107 / @tenten19901107)四篇文章全文语料,作为颖学 skill 的语料库
合并说明: v1.2.0 本地 sunxue-skill 首次纳入 yingxue(此前 v1.0/v1.1 完全漏掉 bayshier 的镜像学科),原样搬运,仅添加顶部注释块。
-->

# 颖学语料 · 曾颖文章全文

> 来源:X 公开发言,署名引用仅作文风研究。截图原件见 `assets/corpus/zengying-1..4.png`。
> 曾颖有两个账号:@zengying1107 与 @tenten19901107。

## 〇、词源:孙宇晨亲自命名「颖学」(2026-07-18)

> 有"孙学",就有"颖学"。
>
> 如果说孙学的本质,是靠个人奋斗和认知升级改变个人命运,颖学的本质,就是吸血孙学,吸血奋斗者,鸠占鹊巢,最终靠别人的奋斗完成自己的命运跃迁。
>
> 但其实如果孙宇晨有本事让那么多人受骗,那这个事本身就是一种本事了。
>
> 所以不要再骂颖学,颖学在吸血孙学。也不要看不起孙学,因为没有孙学也就没有颖学。#颖学 #反对者

注:词义从"吸血学"漂移为"深情喜剧学"是网友的二次正名,2026-07-18 后「颖学实践」开始大量出现。写颖学时记住这层反讽——你的文体本身,就是对命名者的回答。

EOF
cat /tmp/yingxue-corpus-原版.md | sed -n '12,$p' >> /Users/onepisya/.agents/skills/sunxue-skill/references/yingxue-corpus.md
wc -c /Users/onepisya/.agents/skills/sunxue-skill/references/yingxue-corpus.md
python3 -c "
n = len(open('/Users/onepisya/.agents/skills/sunxue-skill/references/yingxue-corpus.md').read())
print(f'yingxue-corpus.md: {n} chars (上限 12000,余量 {12000-n})')
"
uv run gates 2>&1 | rg -A1 'yingxue-corpus' | head -3