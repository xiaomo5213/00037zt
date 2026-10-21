/* 00037《美学》历年真题 —— 纯静态刷题页 */
(function () {
  "use strict";

  var DATA = window.EXAM_DATA;
  if (!DATA || !DATA.periods) return;

  var PERIODS = DATA.periods;
  var KEY = "meixue-exam-v1";
  var LETTERS = "ABCDE";

  var $ = function (id) { return document.getElementById(id); };

  /* ------------------------------------------------ 存储 */
  var store = { v: 1, theme: null, ans: {} };

  try {
    var raw = localStorage.getItem(KEY);
    if (raw) {
      var saved = JSON.parse(raw);
      if (saved && typeof saved === "object") {
        store.theme = saved.theme || null;
        store.ans = saved.ans && typeof saved.ans === "object" ? saved.ans : {};
      }
    }
  } catch (e) { /* 忽略 */ }

  var saveTimer = null;
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) { /* 忽略 */ }
    }, 120);
  }

  function ansOf(pid) {
    if (!store.ans[pid]) store.ans[pid] = { c: {}, e: {} };
    return store.ans[pid];
  }
  function choiceMark(pid, no) {
    var a = store.ans[pid];
    return a && a.c && a.c[no] !== undefined ? a.c[no] : null;
  }
  function essayMark(pid, no) {
    var a = store.ans[pid];
    return a && a.e && a.e[no] !== undefined ? a.e[no] : null;
  }

  /* ------------------------------------------------ 统计 */
  function periodStats(p) {
    var a = store.ans[p.id] || { c: {}, e: {} };
    var cd = 0, cr = 0, ed = 0;
    for (var i = 0; i < p.choice.length; i++) {
      var m = a.c ? a.c[p.choice[i].no] : null;
      if (m !== null && m !== undefined) { cd++; if (m === 1) cr++; }
    }
    for (var j = 0; j < p.essay.length; j++) {
      var n = a.e ? a.e[p.essay[j].no] : null;
      if (n !== null && n !== undefined) ed++;
    }
    return { cd: cd, cr: cr, ed: ed, total: p.choice.length + p.essay.length };
  }

  function globalStats() {
    var answered = 0, right = 0, total = 0, wrong = 0;
    PERIODS.forEach(function (p) {
      var a = store.ans[p.id] || { c: {}, e: {} };
      total += p.choice.length + p.essay.length;
      p.choice.forEach(function (q) {
        var m = a.c ? a.c[q.no] : null;
        if (m !== null && m !== undefined) { answered++; if (m === 1) right++; else wrong++; }
      });
      p.essay.forEach(function (q) {
        var m = a.e ? a.e[q.no] : null;
        if (m !== null && m !== undefined) { answered++; if (m === 0 || m === 1) wrong++; }
      });
    });
    return { answered: answered, right: right, total: total, wrong: wrong };
  }

  /* ------------------------------------------------ 会话 */
  var session = null;
  var ui = { picked: [], graded: false, revealed: false };

  function periodById(pid) {
    for (var i = 0; i < PERIODS.length; i++) if (PERIODS[i].id === pid) return PERIODS[i];
    return null;
  }

  function listForPeriod(p, mode) {
    if (mode === "choice") {
      return p.choice.map(function (q) { return { pid: p.id, type: "choice", no: q.no }; });
    }
    return p.essay.map(function (q) { return { pid: p.id, type: "essay", no: q.no }; });
  }

  function startPeriod(pid, mode) {
    var p = periodById(pid);
    if (!p) return;
    var list = listForPeriod(p, mode);
    var first = 0;
    for (var i = 0; i < list.length; i++) {
      var done = mode === "choice" ? choiceMark(pid, list[i].no) !== null : essayMark(pid, list[i].no) !== null;
      if (!done) { first = i; break; }
    }
    session = {
      kind: "period", pid: pid, mode: mode, list: list, idx: first,
      tabbed: true, title: p.label, sub: mode === "choice" ? "选择题" : "主观题"
    };
    showPractice();
    renderQuestion();
  }

  function startWrong() {
    var list = [];
    PERIODS.forEach(function (p) {
      p.choice.forEach(function (q) {
        if (choiceMark(p.id, q.no) === 0) list.push({ pid: p.id, type: "choice", no: q.no });
      });
      p.essay.forEach(function (q) {
        var m = essayMark(p.id, q.no);
        if (m === 0 || m === 1) list.push({ pid: p.id, type: "essay", no: q.no });
      });
    });
    if (!list.length) {
      alert("错题本是空的：先做几道题吧。");
      return;
    }
    session = { kind: "wrong", list: list, idx: 0, tabbed: false, title: "错题本", sub: "共 " + list.length + " 题" };
    showPractice();
    renderQuestion();
  }

  function startRandom(n) {
    var pool = [];
    PERIODS.forEach(function (p) {
      p.choice.forEach(function (q) { pool.push({ pid: p.id, type: "choice", no: q.no }); });
    });
    for (var i = pool.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = pool[i]; pool[i] = pool[j]; pool[j] = t;
    }
    session = {
      kind: "random", list: pool.slice(0, n || 20), idx: 0, tabbed: false,
      title: "随机练习", sub: "20 道选择题"
    };
    showPractice();
    renderQuestion();
  }

  /* ------------------------------------------------ 视图切换 */
  function showHome() {
    session = null;
    $("home").hidden = false;
    $("practice").hidden = true;
    renderHome();
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function showPractice() {
    $("home").hidden = true;
    $("practice").hidden = false;
    $("modeTabs").hidden = !session.tabbed;
    if (session.tabbed) {
      var p = periodById(session.pid);
      Array.prototype.forEach.call($("modeTabs").querySelectorAll("button"), function (b) {
        var mode = b.getAttribute("data-mode");
        b.classList.toggle("is-on", mode === session.mode);
        b.textContent = (mode === "choice" ? "选择题 " : "简答题 ") +
          (p ? (mode === "choice" ? p.choice.length : p.essay.length) : "");
      });
    }
    $("pTitle").textContent = session.title;
    $("pSub").textContent = session.sub || "";
  }

  /* ------------------------------------------------ 首页 */
  function renderHome() {
    var g = globalStats();
    $("heroSub").textContent = PERIODS.length + " 套 · " + DATA.meta.choice + " 道选择题 · " + DATA.meta.essay + " 道主观题";
    $("brandSub").textContent = "2016.4 — 2026.4 · " + PERIODS.length + " 套";
    var wc = $("wrongCount");
    wc.textContent = g.wrong;
    wc.setAttribute("data-zero", g.wrong ? "0" : "1");
    $("topProgress").style.width = (g.total ? g.answered / g.total * 100 : 0) + "%";

    var grid = $("periodGrid");
    grid.innerHTML = "";
    PERIODS.forEach(function (p) {
      var st = periodStats(p);
      var done = st.cd + st.ed;
      var pct = st.total ? Math.round(done / st.total * 100) : 0;
      var card = document.createElement("button");
      card.type = "button";
      card.className = "period-card";
      card.setAttribute("data-pid", p.id);
      card.innerHTML =
        '<div class="pc-top"><span class="pc-label">' + esc(p.label) + '</span>' +
        '<span class="pc-tag">' + p.choice.length + " 选择 · " + p.essay.length + " 主观</span></div>" +
        '<div class="pc-meta">选择题 ' + st.cd + "/" + p.choice.length +
        "　主观题 " + st.ed + "/" + p.essay.length + "</div>" +
        '<div class="pc-bar"><i style="width:' + pct + '%"></i></div>' +
        '<div class="pc-state' + (pct === 100 ? " done" : "") + '">' +
        (pct === 100 ? "已完成" : done ? "已做 " + done + " / " + st.total + "（" + pct + "%）" : "未开始") +
        "</div>";
      card.addEventListener("click", function () { startPeriod(p.id, "choice"); });
      grid.appendChild(card);
    });
  }

  /* ------------------------------------------------ 题目 */
  function currentItem() {
    return session && session.list ? session.list[session.idx] : null;
  }

  function findChoice(pid, no) {
    var p = periodById(pid);
    if (!p) return null;
    for (var i = 0; i < p.choice.length; i++) if (p.choice[i].no === no) return p.choice[i];
    return null;
  }
  function findEssay(pid, no) {
    var p = periodById(pid);
    if (!p) return null;
    for (var i = 0; i < p.essay.length; i++) if (p.essay[i].no === no) return p.essay[i];
    return null;
  }

  function renderQuestion() {
    if (!session) return;
    if (session.idx >= session.list.length) { renderDone(); return; }
    if (session.idx < 0) session.idx = 0;

    var item = currentItem();
    var q = item.type === "choice" ? findChoice(item.pid, item.no) : findEssay(item.pid, item.no);
    if (!q) { session.idx++; renderQuestion(); return; }

    ui = { picked: [], graded: false, revealed: false };

    $("pTitle").textContent = session.kind === "period" ? periodById(item.pid).label : session.title;
    $("pSub").textContent = session.kind === "period"
      ? (item.type === "choice" ? "选择题" : "主观题") + " · 共 " + session.list.length + " 题"
      : (periodById(item.pid) ? periodById(item.pid).label + " · " : "") + (item.type === "choice" ? "选择题" : "主观题");
    $("pCount").textContent = (session.idx + 1) + " / " + session.list.length;
    $("pBar").style.width = (session.idx / session.list.length * 100) + "%";
    $("prevBtn").disabled = session.idx === 0;

    if (item.type === "choice") renderChoice(item, q);
    else renderEssay(item, q);

    renderDots();
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function renderDots() {
    var answered = 0, right = 0;
    session.list.forEach(function (it) {
      if (it.type === "choice") {
        var m = choiceMark(it.pid, it.no);
        if (m !== null) { answered++; if (m === 1) right++; }
      } else {
        var e = essayMark(it.pid, it.no);
        if (e !== null) answered++;
      }
    });
    $("qnavDots").textContent = answered ? "已答 " + answered + " · 对 " + right : "";
  }

  function renderChoice(item, q) {
    var prev = choiceMark(item.pid, q.no);
    var html =
      '<div class="qhead"><span class="tag">' + (q.multi ? "多选题" : "单选题") + "</span>" +
      '<span class="qno">第 ' + q.no + " 题</span></div>" +
      '<h2 class="qtext">' + esc(q.t) + "</h2>" +
      '<div class="opts" id="opts">';
    q.o.forEach(function (opt, i) {
      html += '<button type="button" class="opt" data-i="' + i + '">' +
        '<span class="letter">' + LETTERS[i] + "</span><span>" + esc(opt) + "</span></button>";
    });
    html += '</div><div class="qactions" id="qactions"></div><div class="explain" id="explain" hidden></div>';
    $("qcard").innerHTML = html;

    Array.prototype.forEach.call($("opts").querySelectorAll(".opt"), function (btn) {
      btn.addEventListener("click", function () { onPick(parseInt(btn.getAttribute("data-i"), 10)); });
    });

    if (prev !== null) {
      ui.graded = true;
      $("opts").classList.add("locked");
      markCorrect(q);
      $("qactions").innerHTML = "";
      showExplain(q, prev === 1, []);
      $("nextBtn").textContent = session.idx + 1 >= session.list.length ? "完成" : "下一题";
    } else {
      $("nextBtn").textContent = "跳过";
      if (q.multi) {
        $("qactions").innerHTML = '<button class="btn primary small" id="checkBtn" type="button" disabled>确认答案</button>' +
          '<span class="hint">多选题：选好后点确认</span>';
        $("checkBtn").addEventListener("click", function () { if (ui.picked.length) gradeChoice(q); });
      } else {
        $("qactions").innerHTML = '<span class="hint">点选项即判分</span>';
      }
    }
  }

  function onPick(i) {
    if (ui.graded) return;
    var item = currentItem();
    var q = findChoice(item.pid, item.no);
    if (!q) return;

    if (q.multi) {
      var at = ui.picked.indexOf(i);
      if (at === -1) ui.picked.push(i); else ui.picked.splice(at, 1);
      Array.prototype.forEach.call($("opts").querySelectorAll(".opt"), function (btn, k) {
        btn.classList.toggle("is-picked", ui.picked.indexOf(k) !== -1);
      });
      var cb = $("checkBtn");
      if (cb) cb.disabled = ui.picked.length === 0;
      return;
    }
    ui.picked = [i];
    gradeChoice(q);
  }

  function gradeChoice(q) {
    var item = currentItem();
    var picked = ui.picked.slice().sort(function (a, b) { return a - b; });
    var correct = q.a.slice().sort(function (a, b) { return a - b; });
    var right = picked.length === correct.length && picked.every(function (v, i) { return v === correct[i]; });

    ui.graded = true;
    var a = ansOf(item.pid);
    a.c[item.no] = right ? 1 : 0;
    save();

    $("opts").classList.add("locked");
    Array.prototype.forEach.call($("opts").querySelectorAll(".opt"), function (btn, k) {
      btn.classList.remove("is-picked");
      if (correct.indexOf(k) !== -1) btn.classList.add("is-right");
      else if (picked.indexOf(k) !== -1) btn.classList.add("is-wrong");
    });
    $("qactions").innerHTML = "";
    showExplain(q, right, picked);
    $("nextBtn").textContent = session.idx + 1 >= session.list.length ? "完成" : "下一题";
    renderDots();
    updateChrome();
  }

  function markCorrect(q) {
    Array.prototype.forEach.call($("opts").querySelectorAll(".opt"), function (btn, k) {
      if (q.a.indexOf(k) !== -1) btn.classList.add("is-right");
    });
  }

  function showExplain(q, right, picked) {
    var box = $("explain");
    var detail = "";
    if (!right && picked.length) {
      var miss = q.a.filter(function (x) { return picked.indexOf(x) === -1; });
      var extra = picked.filter(function (x) { return q.a.indexOf(x) === -1; });
      var bits = [];
      if (miss.length) bits.push("漏选 " + miss.map(function (i) { return LETTERS[i]; }).join("、"));
      if (extra.length) bits.push("错选 " + extra.map(function (i) { return LETTERS[i]; }).join("、"));
      detail = bits.length ? "（" + bits.join("；") + "）" : "";
    }
    var html = '<div class="verdict ' + (right ? "ok" : "bad") + '">' +
      (right ? "回答正确" : "回答错误，正确答案：" + q.a.map(function (i) { return LETTERS[i]; }).join("") +
        (q.multi && picked.length ? detail : "")) +
      "</div>";
    html += "<h3>解析</h3>";
    html += q.exp ? "<p>" + esc(q.exp) + "</p>" : '<p class="muted">原卷未附解析。</p>';
    box.innerHTML = html;
    box.hidden = false;
  }

  function renderEssay(item, q) {
    var prev = essayMark(item.pid, q.no);
    var html =
      '<div class="qhead"><span class="tag">' + esc(q.type || "简答") + "</span>" +
      '<span class="qno">第 ' + q.no + " 题</span></div>" +
      '<h2 class="qtext">' + esc(q.t) + "</h2>" +
      '<div class="qactions"><button class="btn primary small" id="revealBtn" type="button">显示参考答案</button>' +
      '<span class="hint">先自己回忆，再看答案</span></div>' +
      '<div class="answer" id="answerBox" hidden>' +
      '<div class="block"><h3>参考答案</h3>' + paras(q.ans) + "</div>" +
      (q.exp ? '<div class="block"><h3>解析</h3>' + paras(q.exp) + "</div>" : "") +
      "</div>" +
      '<div class="selfgrade" id="selfGrade" hidden><span class="label">这道题你：</span>' +
      '<button type="button" class="self-btn" data-v="2">会了</button>' +
      '<button type="button" class="self-btn" data-v="1">有点模糊</button>' +
      '<button type="button" class="self-btn" data-v="0">不会</button></div>';
    $("qcard").innerHTML = html;

    $("revealBtn").addEventListener("click", function () {
      ui.revealed = true;
      $("answerBox").hidden = false;
      $("selfGrade").hidden = false;
      $("revealBtn").parentNode.hidden = true;
    });

    var btns = $("selfGrade").querySelectorAll(".self-btn");
    Array.prototype.forEach.call(btns, function (b) {
      if (prev !== null && parseInt(b.getAttribute("data-v"), 10) === prev) b.classList.add("is-on");
      b.addEventListener("click", function () {
        var v = parseInt(b.getAttribute("data-v"), 10);
        var a = ansOf(item.pid);
        a.e[item.no] = v;
        save();
        Array.prototype.forEach.call(btns, function (x) { x.classList.remove("is-on"); });
        b.classList.add("is-on");
        renderDots();
        updateChrome();
        $("nextBtn").focus({ preventScroll: true });
      });
    });

    $("nextBtn").textContent = session.idx + 1 >= session.list.length ? "完成" : "下一题";
  }

  /* ------------------------------------------------ 完成页 */
  function renderDone() {
    var total = session.list.length;
    var answered = 0, right = 0;
    session.list.forEach(function (it) {
      if (it.type === "choice") {
        var m = choiceMark(it.pid, it.no);
        if (m !== null) { answered++; if (m === 1) right++; }
      } else if (essayMark(it.pid, it.no) !== null) answered++;
    });
    $("pCount").textContent = total + " / " + total;
    $("pBar").style.width = "100%";
    $("prevBtn").disabled = false;
    $("nextBtn").hidden = true;
    $("qcard").innerHTML =
      '<div class="qhead"><span class="tag">完成</span></div>' +
      '<h2 class="qtext">这一组刷完了</h2>' +
      '<p class="done-line">共 ' + total + " 题，已答 " + answered + " 题" +
      (session.kind !== "period" ? "" : "，选择题答对 " + right + " 题") + "。</p>" +
      '<div class="qactions"><button class="btn primary small" id="homeBtn2" type="button">返回首页</button>' +
      '<button class="btn ghost small" id="againBtn2" type="button">再刷一遍</button></div>';
    $("homeBtn2").addEventListener("click", showHome);
    $("againBtn2").addEventListener("click", function () {
      session.idx = 0;
      $("nextBtn").hidden = false;
      renderQuestion();
    });
    renderDots();
  }

  /* ------------------------------------------------ 工具 */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
    });
  }
  function paras(text) {
    if (!text) return "<p>暂无。</p>";
    return String(text).split("\n").filter(function (x) { return x.trim(); })
      .map(function (x) { return "<p>" + esc(x) + "</p>"; }).join("");
  }

  function updateChrome() {
    var g = globalStats();
    var wc = $("wrongCount");
    wc.textContent = g.wrong;
    wc.setAttribute("data-zero", g.wrong ? "0" : "1");
    $("topProgress").style.width = (g.total ? g.answered / g.total * 100 : 0) + "%";
  }

  /* ------------------------------------------------ 导航 */
  function go(delta) {
    if (!session) return;
    var next = session.idx + delta;
    if (next < 0) return;
    if (next >= session.list.length) { session.idx = session.list.length; renderQuestion(); return; }
    session.idx = next;
    renderQuestion();
  }

  /* ------------------------------------------------ 事件 */
  function bind() {
    $("brandHome").addEventListener("click", showHome);
    $("brandHome").addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showHome(); }
    });
    $("backBtn").addEventListener("click", showHome);
    $("prevBtn").addEventListener("click", function () { go(-1); });
    $("nextBtn").addEventListener("click", function () {
      $("nextBtn").hidden = false;
      go(1);
    });
    $("randomBtn").addEventListener("click", function () { startRandom(20); });
    $("wrongHeroBtn").addEventListener("click", startWrong);
    $("wrongBtn").addEventListener("click", startWrong);

    $("modeTabs").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-mode]");
      if (!b || !session || !session.tabbed) return;
      var mode = b.getAttribute("data-mode");
      if (mode === session.mode) return;
      startPeriod(session.pid, mode);
    });

    $("themeBtn").addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      store.theme = next;
      save();
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", next === "dark" ? "#161512" : "#f6f3ec");
    });

    window.addEventListener("scroll", function () {
      document.body.classList.toggle("is-scrolled", window.scrollY > 8);
    }, { passive: true });

    document.addEventListener("keydown", function (e) {
      if (e.target instanceof Element && e.target.matches("input, textarea, select")) return;

      if (e.key === "Escape") { showHome(); return; }
      if (!session || $("practice").hidden) return;

      var item = currentItem();
      if (!item) return;

      if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); return; }
      if (e.key === "ArrowRight") { e.preventDefault(); go(1); return; }

      if (item.type === "choice") {
        var q = findChoice(item.pid, item.no);
        if (!q) return;
        if (!ui.graded) {
          var letter = e.key.toUpperCase();
          var i = LETTERS.indexOf(letter);
          if (i !== -1 && i < q.o.length) { e.preventDefault(); onPick(i); return; }
          if (q.multi && (e.key === "Enter") && ui.picked.length) { e.preventDefault(); gradeChoice(q); return; }
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(1); }
        } else if (e.key === "Enter" || e.key === " ") {
          e.preventDefault(); go(1);
        }
        return;
      }

      // 主观题
      if (!ui.revealed && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        if ($("revealBtn")) $("revealBtn").click();
        return;
      }
      if (ui.revealed && ["1", "2", "3"].indexOf(e.key) !== -1) {
        e.preventDefault();
        var map = { "1": 2, "2": 1, "3": 0 };
        var btn = $("selfGrade").querySelector('.self-btn[data-v="' + map[e.key] + '"]');
        if (btn) btn.click();
        return;
      }
      if (e.key === "Enter") { e.preventDefault(); go(1); }
    });
  }

  /* ------------------------------------------------ 启动 */
  if (store.theme) {
    document.documentElement.setAttribute("data-theme", store.theme);
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute("content", store.theme === "dark" ? "#161512" : "#f6f3ec");
  }
  bind();
  renderHome();
  updateChrome();
})();
