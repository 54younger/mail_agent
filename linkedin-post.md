# LinkedIn post — Mail Agent

Two drafts (English / 中文). Pick one, or mix. Line breaks are kept short on purpose —
that's how posts actually read on LinkedIn.

---

## English

I applied to a lot of jobs this year.

Somewhere around the 40th application I'd already lost track of who had even replied. Confirmations, OA links, all the "unfortunately, we've decided..." emails — buried in my inbox, some in English, some in Swedish.

So over a few weekends I built a small tool to sort it out for myself. It's called Mail Agent.

It reads my inbox over IMAP and turns it into a board of every application: company, role, date applied, and where it currently stands.

The extraction runs in a few steps, mostly so it doesn't burn through API credits:

- first it drops anything that clearly isn't job-related, so newsletters never get looked at
- then a small, cheap model checks "is this actually about one of my applications?"
- then a stronger model pulls out the company, role and current status, and merges all the emails from the same company into one entry

Once it's on the board there's a little dashboard on top — interviews, offer rate, applications over time. And if it reads a status wrong, I just fix it by hand and it stops overriding me.

One thing I didn't want to give up: my email never actually leaves my laptop.

The frontend is hosted on Vercel, but the backend runs locally. You download the backend from the GitHub releases page (one file for Windows/Mac/Linux, or Docker if you'd rather), double-click it, then open the site. No account, no server in the middle — your inbox and API keys stay on your own machine.

It's open source, and honestly still rough in a few places.

If you're job hunting right now, or building things with LLMs, I'd really like to hear what you think.

Live: mail-agent-hazel.vercel.app
Code: github.com/54younger/mail_agent

#buildinpublic #opensource #llm

---

## 中文

今年投了很多简历。

大概投到第 40 家的时候，我已经记不清到底哪些回过我了。投递确认、测评链接、各种"很遗憾"，全埋在邮箱里，有中文的也有英文的。

于是花了几个周末，给自己写了个小工具，叫 Mail Agent。

它通过 IMAP 读我的邮箱，把每一次投递整理成一块看板：公司、职位、投递时间、现在走到了哪一步。

抽取分成了几步，主要是不想把 API 的钱烧光：

- 先把明显跟求职无关的邮件过滤掉，营销邮件根本不会被读
- 再用一个便宜的小模型判断"这封到底跟我投的岗位有没有关系"
- 最后用强一点的模型抽出公司、职位和当前状态，并把同一家公司的邮件归并成一条

进了看板之后，上面有个小面板：进了几场面试、offer 率、投递随时间的变化。如果它状态判错了，我手动改一下，它就不会再来覆盖我。

有一点我不太想妥协：我的邮件其实一封都没离开过我的电脑。

前端部署在 Vercel 上，后端跑在本地。后端从 GitHub 的 releases 页面下载（Windows/Mac/Linux 各一个文件，嫌麻烦也可以用 Docker），双击运行，再打开网页就行。没有账号，中间也没有服务器，邮箱和密钥都留在你自己机器上。

项目开源了，说实话有些地方还挺糙。

如果你也在找工作，或者在用 LLM 折腾东西，挺想听听你的想法。

在线：mail-agent-hazel.vercel.app
代码：github.com/54younger/mail_agent

#开源 #求职 #LLM
