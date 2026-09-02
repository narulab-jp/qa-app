/* 一問一答アプリ　ロジック
   科目に依存しない。表示する語はすべてデータ（subjects.json / 科目JSON）から取る。
   判定ロジック（norm / judge）は動作確認済みのものをそのまま使っている。変更しないこと。 */
"use strict";

/* ================= 状態 ================= */
var DEFAULT_SETTINGS = {graduateStreak:2, defaultCount:20, autoMic:false, fontSize:"normal"};

var SUBJECTS = [];      // subjects.json
var SUBJECT = null;     // 選択中の科目データ
var SEQMAP = {};        // seq → {q, unit}
var picked = {};        // 選んだ単元 id → true
var cfg = {mode:"normal", count:20, level:"SA", order:"shuffle"};
var noteCfg = {order:"wrong", count:10};

var note = null;        // 間違いノート
var noteLoaded = false; // ファイルから読み込んだか
var noteAsked = false;  // 「ノートなしで始めますか」を尋ねたか
var logs = null;        // 学習ログ
var dirty = false;      // 未保存の変更があるか

var quiz = null;        // 出題の進行
var session = null;     // 学習ログ1件分
var lastPool = [];      // 「同じ範囲でもう一度」用
var current = null, currentItem = null, currentUser = "", shownAt = 0, answered = false;
var rec = null, listening = false, speechBlocked = false, kbdSticky = false;
var SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
var timerId = null;

window.__micLog = [];   /* 動作確認用の記録（機能には影響しない） */

function $(id){ return document.getElementById(id); }
function show(id){
  ["s-home","s-unit","s-setup","s-quiz","s-judge","s-result","s-note",
   "s-settings","s-print"].forEach(function(s){ $(s).hidden = (s !== id); });
  window.scrollTo(0,0);
}
function esc(s){
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function label(){ return (SUBJECT && SUBJECT.unitLabel) || "単元"; }
function nowIso(){
  var d = new Date(), z = -d.getTimezoneOffset();
  function p(n){ return (n<10?"0":"") + n; }
  return d.getFullYear() + "-" + p(d.getMonth()+1) + "-" + p(d.getDate()) + "T" +
         p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds()) +
         (z>=0?"+":"-") + p(Math.floor(Math.abs(z)/60)) + ":" + p(Math.abs(z)%60);
}
function mmss(sec){
  sec = Math.max(0, Math.floor(sec));
  var m = Math.floor(sec/60), s = sec%60;
  return m + "分" + (s<10?"0":"") + s + "秒";
}
function setDirty(v){ dirty = v; }

/* ============ 表記ゆれの正規化（変更しないこと） ============ */
function norm(s){
  if(s === null || s === undefined) return "";
  var t = String(s);
  if(t.normalize) t = t.normalize("NFKC");          // 全角・半角の統一
  t = t.replace(/[ァ-ヶ]/g, function(c){            // カタカナ→ひらがな
    return String.fromCharCode(c.charCodeAt(0) - 0x60);
  });
  t = t.toLowerCase();
  t = t.replace(/^(?:えーと|えっと|ええと|あのー|あの|そのー|答えは|こたえは)+/,"");
  var prev;
  do{
    prev = t;
    t = t.replace(/(?:だと思います|と思います|でしょうか|でしょう|ですね|ですか|でした|かなあ|かな|です|ます|だよ|だね|だと|よ|ね|？|\?|。|、)$/,"");
  }while(t !== prev);
  t = t.replace(/[\s　]/g,"");
  t = t.replace(/[、。・,.\-−‐―ー─－_(){}\[\]（）「」『』【】:：;；!！?？'"’”`~＝=]/g,"");
  return t;
}
/* ============ 自動判定（変更しないこと） ============ */
function judge(user, q){
  var nu = norm(user);
  if(!nu) return false;
  var cands = [q.a].concat(q.accept || []);
  for(var i=0;i<cands.length;i++){
    var nc = norm(cands[i]);
    if(!nc) continue;
    if(nu === nc) return true;
    var sh = nu.length <= nc.length ? nu : nc;
    var lo = nu.length <= nc.length ? nc : nu;
    if(sh.length >= 3 && lo.indexOf(sh) >= 0 && (sh.length / lo.length) >= 0.5) return true;
  }
  return false;
}
/* 判定方式はデータ側のフラグで決める（アプリ側で出題タイプを条件にしない） */
function isSelfCheck(q){ return q.selfCheck === true; }

/* ================= 読み込み ================= */
function getJSON(path){
  return fetch(path).then(function(r){
    if(!r.ok) throw new Error("HTTP " + r.status + " : " + path);
    return r.json();
  });
}
function showLoadError(msg){
  var el = $("loadError");
  el.hidden = false;
  el.innerHTML =
    '<div class="banner">データを読み込めませんでした。<br>' + esc(msg) + '<br><br>' +
    'ファイルをダブルクリックで開いた場合、ブラウザの安全上の制限で同じフォルダの' +
    'データを自動で読めないことがあります。README.md の「起動方法」をご覧ください。</div>';
}

/* ================= 間違いノート ================= */
function newNote(){
  return {subjectId:(SUBJECT?SUBJECT.subjectId:null), updated:nowIso(),
          entries:[], history:[], settings:JSON.parse(JSON.stringify(DEFAULT_SETTINGS))};
}
function settings(){ return (note && note.settings) || DEFAULT_SETTINGS; }
function findEntry(seq){
  for(var i=0;i<note.entries.length;i++) if(note.entries[i].seq === seq) return note.entries[i];
  return null;
}
/* 出入りの規則：間違えたら追加/加算、正解したら連続数を増やし、規定回で卒業 */
function updateNote(item, ok){
  var seq = item.q.seq, e = findEntry(seq), r = {added:false, graduated:false};
  if(!ok){
    if(e){ e.wrongCount++; e.correctStreak = 0; e.lastWrong = nowIso(); }
    else{
      note.entries.push({seq:seq, unitId:item.unit.id, no:item.q.no,
                         wrongCount:1, correctStreak:0,
                         firstWrong:nowIso(), lastWrong:nowIso(), lastCorrect:null});
      r.added = true;
    }
  }else if(e){
    e.correctStreak++;
    e.lastCorrect = nowIso();
    if(e.correctStreak >= settings().graduateStreak){
      note.entries = note.entries.filter(function(x){ return x.seq !== seq; });
      r.graduated = true;
    }
  }
  note.updated = nowIso();
  setDirty(true);
  return r;
}
function noteItems(order){
  var out = [];
  note.entries.forEach(function(e){
    var m = SEQMAP[e.seq];
    if(m) out.push({item:m, entry:e});
  });
  if(order === "recent"){
    out.sort(function(a,b){ return (a.entry.lastWrong < b.entry.lastWrong) ? 1 : -1; });
  }else if(order === "random"){
    for(var i=out.length-1;i>0;i--){
      var j = Math.floor(Math.random()*(i+1)), t = out[i]; out[i]=out[j]; out[j]=t;
    }
  }else{  // 既定：よく間違える順
    out.sort(function(a,b){
      if(b.entry.wrongCount !== a.entry.wrongCount)
        return b.entry.wrongCount - a.entry.wrongCount;
      return (a.entry.lastWrong < b.entry.lastWrong) ? 1 : -1;
    });
  }
  return out;
}

/* ================= 学習ログ ================= */
function newLogs(){ return {subjectId:(SUBJECT?SUBJECT.subjectId:null), sessions:[]}; }
function newSession(mode, units, round){
  var d = new Date();
  function p(n){ return (n<10?"0":"")+n; }
  return {
    sessionId: "" + d.getFullYear() + p(d.getMonth()+1) + p(d.getDate()) + "-" +
               p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds()),
    subjectId: SUBJECT.subjectId, mode: mode, units: units, round: round || 1,
    startedAt: nowIso(), endedAt: null, elapsedSec: 0,
    totalAsked: 0, firstTryCorrect: 0, firstTryRate: 0, completed: false,
    byType: {}, byLevel: {}, slowest: [],
    _seen: {}, _times: [], _t0: Date.now(), _base: 0,
    _noteAdded: 0, _noteGraduated: 0
  };
}
function sessionElapsed(){
  if(!session) return 0;
  return session._base + (Date.now() - session._t0) / 1000;
}
function bump(obj, key, ok){
  if(!obj[key]) obj[key] = {asked:0, correct:0};
  obj[key].asked++;
  if(ok) obj[key].correct++;
}
function recordAnswer(item, ok, sec){
  var q = item.q;
  session._times.push({seq:q.seq, sec:Math.round(sec)});
  if(!session._seen[q.seq]){           // 初回解答だけを正答率の対象にする
    session._seen[q.seq] = true;
    session.totalAsked++;
    if(ok) session.firstTryCorrect++;
    bump(session.byType, q.type, ok);
    bump(session.byLevel, q.level, ok);
  }
}
function finishSession(completed){
  if(!session) return;
  session.endedAt = nowIso();
  session.elapsedSec = Math.round(sessionElapsed());
  session.completed = !!completed;
  session.firstTryRate = session.totalAsked
    ? Math.round(session.firstTryCorrect / session.totalAsked * 1000) / 1000 : 0;
  var t = session._times.slice().sort(function(a,b){ return b.sec - a.sec; });
  var seen = {}, top = [];
  for(var i=0;i<t.length && top.length<10;i++){
    if(seen[t[i].seq]) continue;
    seen[t[i].seq] = true;
    top.push({seq:t[i].seq, sec:t[i].sec});
  }
  session.slowest = top;
  var out = JSON.parse(JSON.stringify(session));
  ["_seen","_times","_t0","_base","_noteAdded","_noteGraduated"].forEach(function(k){
    delete out[k];
  });
  logs.sessions.push(out);
  setDirty(true);
}

/* ================= ファイルの保存・読み込み ================= */
function download(name, obj){
  var blob = new Blob([JSON.stringify(obj, null, 1)], {type:"application/json"});
  var url = URL.createObjectURL(blob);
  var a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a);
  a.click();
  setTimeout(function(){ URL.revokeObjectURL(url); a.parentNode.removeChild(a); }, 1500);
}
function fileBase(){ return (SUBJECT && SUBJECT.subjectId) || "subject"; }
function saveNote(){
  download(fileBase() + "_note.json", note);
  setDirty(false);
  msgNote("ノートを保存しました（" + fileBase() + "_note.json）");
  renderHome();
}
function saveLog(){
  download(fileBase() + "_log.json", logs);
  msgNote("学習ログを保存しました（" + fileBase() + "_log.json）");
}
function msgNote(t){
  var el = $("noteLoadMsg");
  el.hidden = false;
  el.textContent = t;
}
/* 読み込み時の照合：現在の問題データに無い seq は無視し、件数を表示する */
function importNoteText(text){
  var d = JSON.parse(text);
  if(!d || !Array.isArray(d.entries)) throw new Error("ノートの形式が違います");
  var kept = [], ignored = 0;
  d.entries.forEach(function(e){
    if(SEQMAP[e.seq]) kept.push(e); else ignored++;
  });
  note = {
    subjectId: d.subjectId || (SUBJECT ? SUBJECT.subjectId : null),
    updated: d.updated || nowIso(),
    entries: kept,
    history: Array.isArray(d.history) ? d.history : [],
    settings: Object.assign(JSON.parse(JSON.stringify(DEFAULT_SETTINGS)), d.settings || {})
  };
  noteLoaded = true;
  noteAsked = true;
  setDirty(false);
  applySettings();
  renderHome();
  return {loaded: kept.length, ignored: ignored};
}
function importLogText(text){
  var d = JSON.parse(text);
  if(!d || !Array.isArray(d.sessions)) throw new Error("学習ログの形式が違います");
  logs = {subjectId: d.subjectId || fileBase(), sessions: d.sessions};
  renderHome();
  return {sessions: logs.sessions.length};
}
function readFile(input, handler){
  input.addEventListener("change", function(ev){
    var f = ev.target.files && ev.target.files[0];
    if(!f) return;
    var fr = new FileReader();
    fr.onload = function(){
      try{ handler(String(fr.result)); }
      catch(e){ msgNote("読み込めませんでした：" + e.message); }
      input.value = "";
    };
    fr.readAsText(f, "utf-8");
  });
}

/* ================= 確認ダイアログ ================= */
var confirmCb = null;
function askConfirm(msg, cb){
  $("confirmMsg").textContent = msg;
  $("confirmWrap").hidden = false;
  confirmCb = cb;
}
function closeConfirm(v){
  $("confirmWrap").hidden = true;
  var cb = confirmCb; confirmCb = null;
  if(cb) cb(v);
}
/* ノートを読み込まずに始めようとしたら一度だけ確認する */
function ensureNote(go){
  if(noteLoaded || noteAsked){ go(); return; }
  askConfirm("前回のノートを読み込んでいません。ノートなしで始めますか。", function(yes){
    noteAsked = true;
    if(yes) go();
  });
}

/* ================= ホーム ================= */
function renderSubjects(){
  var box = $("subjectList");
  box.innerHTML = "";
  SUBJECTS.forEach(function(s){
    var b = document.createElement("button");
    b.className = "btn";
    b.id = "subj-" + s.id;
    b.disabled = !s.enabled;
    b.textContent = s.name + (s.enabled ? "" : "　― 準備中")
                  + (SUBJECT && SUBJECT.subjectId === s.id ? "　（選択中）" : "");
    if(s.enabled) b.addEventListener("click", function(){ openSubject(s); });
    box.appendChild(b);
  });
  if(!SUBJECTS.length){
    box.innerHTML = '<div class="banner">科目が登録されていません。subjects.json をご確認ください。</div>';
  }
}
function openSubject(s){
  return getJSON(s.file).then(function(d){
    SUBJECT = d;
    SEQMAP = {};
    d.units.forEach(function(u){
      u.questions.forEach(function(q){ SEQMAP[q.seq] = {q:q, unit:u}; });
    });
    picked = {};
    if(!note) note = newNote();
    if(!logs) logs = newLogs();
    note.subjectId = d.subjectId;
    logs.subjectId = d.subjectId;
    cfg.count = settings().defaultCount;
    renderSubjects();
    renderHome();
    show("s-home");
  }).catch(function(e){
    show("s-home");
    showLoadError(String(e.message || e));
  });
}
function renderOptRow(boxId, list, cur, onPick){
  var box = $(boxId);
  box.innerHTML = "";
  box.className = "optrow";
  list.forEach(function(o){
    var b = document.createElement("button");
    b.className = "opt";
    b.textContent = o.label;
    b.setAttribute("aria-pressed", String(o.value === cur));
    b.dataset.val = String(o.value);
    b.addEventListener("click", function(){ onPick(o.value); });
    box.appendChild(b);
  });
}
function renderHome(){
  if(!SUBJECT) return;
  $("noteState").textContent = noteLoaded
    ? ("読み込み済み：" + note.entries.length + "問"
       + (dirty ? "／未保存の変更があります" : "／保存済み"))
    : ("読み込んでいません" + (dirty ? "（未保存の変更があります）" : ""));
  var n = note.entries.length;
  $("noteCount").textContent = n
    ? ("間違いノート（現在 " + n + "問）")
    : "間違いノートは空です";
  $("btnNoteQuiz").disabled = (n === 0);
  renderOptRow("optNoteOrder",
    [{label:"よく間違える順", value:"wrong"},
     {label:"最近間違えた順", value:"recent"},
     {label:"ランダム", value:"random"}],
    noteCfg.order, function(v){ noteCfg.order = v; renderHome(); });
  renderOptRow("optNoteCount",
    [{label:"10問", value:10},{label:"20問", value:20},{label:"全部", value:0}],
    noteCfg.count, function(v){ noteCfg.count = v; renderHome(); });
  $("logState").textContent = "学習ログ：" + (logs ? logs.sessions.length : 0) + "件";
}

/* ================= 単元 ================= */
function renderUnits(){
  $("unitTitle").textContent = SUBJECT.subjectName;
  $("unitLead").textContent = "出題する" + label() + "を選んでください（いくつでも選べます）。";
  var box = $("unitList");
  box.innerHTML = "";
  SUBJECT.units.forEach(function(u){
    var b = document.createElement("button");
    b.className = "unit";
    b.id = "unit-" + u.id;
    b.setAttribute("aria-pressed","false");
    b.innerHTML = '<span class="mark"></span><span class="nm">' +
                  esc(u.id + " " + u.name) + '</span><span class="ct">' +
                  u.questions.length + "問</span>";
    b.addEventListener("click", function(){ picked[u.id] = !picked[u.id]; syncUnits(); });
    box.appendChild(b);
  });
  syncUnits();
}
function syncUnits(){
  var n = 0, q = 0;
  SUBJECT.units.forEach(function(u){
    var on = !!picked[u.id], el = $("unit-" + u.id);
    el.setAttribute("aria-pressed", String(on));
    el.querySelector(".mark").textContent = on ? "✓" : "";
    if(on){ n++; q += u.questions.length; }
  });
  $("unitPicked").textContent =
    n ? ("選択中：" + n + label() + "／" + q + "問") : ("まだ" + label() + "を選んでいません");
  $("btnUnitNext").disabled = (n === 0);
}
function pickedUnits(){
  return SUBJECT.units.filter(function(u){ return picked[u.id]; });
}

/* ================= 設定画面（出題） ================= */
function renderCountOptions(){
  renderOptRow("optCount",
    [{label:"5問", value:5},{label:"10問", value:10},{label:"20問", value:20},
     {label:"選んだ範囲すべて", value:0}],
    cfg.count, function(v){ cfg.count = v; syncOpts(); });
}
function openSetup(){
  var us = pickedUnits();
  $("setupTitle").textContent =
    us.length === 1 ? (us[0].id + " " + us[0].name)
                    : (us.length + label() + "をまとめて出題");
  syncOpts();
  show("s-setup");
}
function syncOpts(){
  renderCountOptions();
  ["mode","level","order"].forEach(function(k){
    var els = document.querySelectorAll("[data-" + k + "]");
    for(var i=0;i<els.length;i++)
      els[i].setAttribute("aria-pressed", String(els[i].dataset[k] === cfg[k]));
  });
  $("fsCount").hidden = (cfg.mode === "round");
  var pool = filterPool();
  var n = (cfg.mode === "round" || cfg.count === 0) ? pool.length
                                                    : Math.min(cfg.count, pool.length);
  $("setupCount").textContent = "この設定での出題数：" + n + "問（対象 " + pool.length + "問中）"
    + (cfg.mode === "round" ? "／全問正解するまで繰り返します" : "");
  $("btnStart").disabled = (pool.length === 0);
}
function filterPool(){
  var out = [];
  pickedUnits().forEach(function(u){
    u.questions.forEach(function(q){
      if(cfg.level === "ALL" || q.level === "S" || q.level === "A") out.push({q:q, unit:u});
    });
  });
  return out;
}
function shuffle(a){
  for(var i=a.length-1;i>0;i--){ var j=Math.floor(Math.random()*(i+1)), t=a[i]; a[i]=a[j]; a[j]=t; }
  return a;
}
function orderPool(pool){
  if(cfg.order === "shuffle") return shuffle(pool.slice());
  return pool.slice().sort(function(a,b){
    if(a.unit.id !== b.unit.id) return a.unit.id < b.unit.id ? -1 : 1;
    return a.q.no - b.q.no;
  });
}

/* ================= 出題の進行 ================= */
function startQuiz(list, mode, units, round, resume){
  quiz = {mode:mode, roundList:list.slice(), queue:list.slice(),
          wrongPass:[], round:round || 1, done:0};
  if(resume){
    quiz.queue = resume.queue;
    quiz.wrongPass = resume.wrongPass;
    quiz.roundList = resume.roundList;
  }
  if(!session || !resume) session = newSession(mode, units, quiz.round);
  startTimer();
  nextQuestion();
}
function startTimer(){
  stopTimer();
  timerId = setInterval(function(){ if(!$("s-quiz").hidden) renderStatus(); }, 1000);
}
function stopTimer(){ if(timerId){ clearInterval(timerId); timerId = null; } }
function renderStatus(){
  var bar = $("statusBar");
  if(quiz.mode === "round"){
    bar.hidden = false;
    bar.textContent = quiz.round + "周目　／　残り " +
      (quiz.queue.length + quiz.wrongPass.length) + "問　／　経過 " + mmss(sessionElapsed());
  }else{
    bar.hidden = false;
    bar.textContent = "経過 " + mmss(sessionElapsed());
  }
}
function nextQuestion(){
  if(!quiz.queue.length){
    if(quiz.mode === "round" && quiz.wrongPass.length){
      quiz.queue = quiz.wrongPass;
      quiz.wrongPass = [];
    }else{
      showResult(quiz.mode === "round");
      return;
    }
  }
  currentItem = quiz.queue[0];
  current = currentItem.q;
  currentUser = "";
  answered = false;
  shownAt = Date.now();
  renderStatus();
  $("mProgress").textContent = quiz.mode === "round"
    ? ("解答 " + (quiz.done + 1) + "問目")
    : ((quiz.done + 1) + " / " + quiz.roundList.length + "問目");
  $("mUnit").textContent = currentItem.unit.id + " " + currentItem.unit.name +
                           " 節" + current.section;
  $("mLevel").textContent = "重要度 " + current.level;
  $("mType").textContent = current.type;
  $("qText").textContent = current.q;
  $("selfNote").hidden = !isSelfCheck(current);
  var h = $("heard");
  h.textContent = "ここに聞き取った内容が表示されます";
  h.className = "heard empty";
  $("kbdBox").hidden = !(speechBlocked || kbdSticky || !SR);
  $("kbdInput").value = "";
  $("btnMic").hidden = !SR;
  $("btnMic").disabled = speechBlocked;
  $("btnMic").className = "btn mic";
  $("btnMic").textContent = "🎤 音声で答える";
  $("btnPause").hidden = (quiz.mode !== "round");
  renderSpeechBanner();
  show("s-quiz");
  if(!$("kbdBox").hidden) $("kbdInput").focus();
  if(settings().autoMic && SR && !speechBlocked && !navigatorOffline()) startMic();
}
function navigatorOffline(){ return (typeof navigator.onLine === "boolean") && !navigator.onLine; }

function renderSpeechBanner(){
  var b = $("speechBanner");
  if(navigatorOffline()){
    b.hidden = false; b.className = "banner";
    b.textContent = "オフラインのため音声認識は使えません。キーボード入力に切り替えました。";
    kbdSticky = true; $("kbdBox").hidden = false;
  }else if(!SR){
    b.hidden = false; b.className = "banner";
    b.textContent = "このブラウザは音声認識に対応していません。キーボード入力で最後までご利用いただけます。";
  }else if(speechBlocked){
    b.hidden = false; b.className = "banner";
    b.textContent = "マイクを利用できないため、キーボード入力に切り替えました。このまま最後までご利用いただけます。";
  }else{
    b.hidden = true;
  }
}
function setHeard(text, interim){
  var h = $("heard");
  if(!text){ h.textContent = "ここに聞き取った内容が表示されます"; h.className = "heard empty"; }
  else{ h.textContent = interim ? (text + " …") : text; h.className = "heard"; }
}

/* ================= 音声認識 ================= */
function startMic(){
  if(!SR || speechBlocked) return;
  try{ rec = new SR(); }
  catch(e){ fallbackToKeyboard("音声認識を開始できませんでした。", false); return; }
  rec.lang = "ja-JP";
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;
  rec.onstart = function(){
    window.__micLog.push("start");
    listening = true;
    $("btnMic").className = "btn mic listening";
    $("btnMic").textContent = "● 認識中…（話し終えたら止まります）";
    setHeard("", false);
  };
  rec.onresult = function(ev){
    var interim = "", final = "";
    for(var i=ev.resultIndex;i<ev.results.length;i++){
      var r = ev.results[i];
      if(r.isFinal) final += r[0].transcript; else interim += r[0].transcript;
    }
    if(final){ setHeard(final, false); submitAnswer(final); }
    else setHeard(interim, true);
  };
  rec.onerror = function(ev){
    var code = ev.error || "";
    window.__micLog.push("error:" + code);
    if(code === "not-allowed" || code === "service-not-allowed"){
      fallbackToKeyboard("マイクの利用が許可されませんでした。", true);
    }else if(code === "no-speech"){
      stopMicUI();
      $("heard").textContent = "聞き取れませんでした。もう一度お試しください。";
      $("heard").className = "heard";
    }else if(code === "network" || code === "audio-capture"){
      fallbackToKeyboard("音声認識サービスに接続できませんでした。", false);
    }else{ stopMicUI(); }
  };
  rec.onend = function(){ window.__micLog.push("end"); stopMicUI(); };
  try{ rec.start(); }
  catch(e){ fallbackToKeyboard("音声認識を開始できませんでした。", false); }
}
function stopMicUI(){
  listening = false;
  var b = $("btnMic");
  b.className = "btn mic";
  b.textContent = "🎤 音声で答える";
}
function fallbackToKeyboard(msg, hard){
  stopMicUI();
  kbdSticky = true;
  if(hard){ speechBlocked = true; $("btnMic").disabled = true; }
  renderSpeechBanner();
  if(msg){
    var b = $("speechBanner");
    b.hidden = false; b.className = "banner";
    b.textContent = msg + " このままキーボード入力で最後までご利用いただけます。"
                  + (hard ? "" : "（マイクをもう一度試すこともできます）");
  }
  $("kbdBox").hidden = false;
  $("kbdInput").focus();
}

/* ================= 判定 ================= */
function submitAnswer(text){
  if(answered) return;                 /* 二重送信を防ぐ */
  if(listening && rec){ try{ rec.stop(); }catch(e){} }
  currentUser = text || "";
  var self = isSelfCheck(current);
  $("jUser").textContent = currentUser ? currentUser : "（未回答）";
  $("jAns").textContent = current.a;
  $("jExp").textContent = current.exp;
  $("jAnsLbl").textContent = self ? "模範解答" : "正解";
  $("judgeSelfNote").hidden = !self;
  $("jNoteMsg").textContent = "";
  if(self && currentUser){
    $("verdict").hidden = true;
    $("selfButtons").hidden = false;
    $("btnNext").hidden = true;
  }else{
    var ok = currentUser ? judge(currentUser, current) : false;
    setVerdict(ok);
    $("selfButtons").hidden = true;
    $("btnNext").hidden = false;
    settle(ok);
  }
  show("s-judge");
}
function setVerdict(ok){
  var v = $("verdict");
  v.hidden = false;
  v.textContent = ok ? "○" : "×";
  v.className = "verdict " + (ok ? "ok" : "ng");
}
function settle(ok){
  if(answered) return;                 /* 同じ問題を二重に記録しない */
  answered = true;
  var sec = (Date.now() - shownAt) / 1000;
  recordAnswer(currentItem, ok, sec);
  var r = updateNote(currentItem, ok);
  if(r.added){ session._noteAdded++; $("jNoteMsg").textContent = "間違いノートに追加しました。"; }
  else if(r.graduated){ session._noteGraduated++;
    $("jNoteMsg").textContent = "連続正解のため、間違いノートから外しました。"; }
  quiz.done++;
  quiz.queue.shift();
  if(!ok && quiz.mode === "round") quiz.wrongPass.push(currentItem);
  quiz.results = quiz.results || [];
  quiz.results.push({item:currentItem, user:currentUser, ok:ok});
}

/* ================= 結果 ================= */
function pct(a, b){ return b ? Math.round(a / b * 1000) / 10 : 0; }
function showResult(completed){
  stopTimer();
  finishSession(completed);
  var res = quiz.results || [];
  var firstOk = session.firstTryCorrect, firstAll = session.totalAsked;
  $("resultTitle").textContent = quiz.mode === "round"
    ? (quiz.round + "周目 完了") : "結果";
  $("score").textContent = "初回正答 " + firstOk + " / " + firstAll + " 問（" +
                           pct(firstOk, firstAll) + "％）";
  var h = "";
  h += '<div class="stat"><h3>このセッション</h3><table>' +
       "<tr><th>所要時間</th><td>" + mmss(session.elapsedSec) + "</td></tr>" +
       "<tr><th>解答した回数</th><td>" + res.length + "回</td></tr>" +
       "<tr><th>初回正答率</th><td>" + pct(firstOk, firstAll) + "％</td></tr>" +
       "<tr><th>ノートに追加</th><td>" + session._noteAdded + "問</td></tr>" +
       "<tr><th>ノートを卒業</th><td>" + session._noteGraduated + "問</td></tr>" +
       "</table></div>";
  function tbl(title, obj){
    var s = '<div class="stat"><h3>' + title + '</h3><table>' +
            "<tr><th>区分</th><th>出題</th><th>正解</th><th>正答率</th></tr>";
    Object.keys(obj).forEach(function(k){
      s += "<tr><td class='l'>" + esc(k) + "</td><td>" + obj[k].asked + "</td><td>" +
           obj[k].correct + "</td><td>" + pct(obj[k].correct, obj[k].asked) + "％</td></tr>";
    });
    return s + "</table></div>";
  }
  if(Object.keys(session.byType).length) h += tbl("出題タイプ別（初回解答）", session.byType);
  if(Object.keys(session.byLevel).length) h += tbl("重要度別（初回解答）", session.byLevel);
  if(session.slowest.length){
    h += '<div class="stat"><h3>時間がかかった問題 上位5問</h3><table>' +
         "<tr><th>秒</th><th>問題</th></tr>";
    session.slowest.slice(0,5).forEach(function(s){
      var m = SEQMAP[s.seq];
      h += "<tr><td>" + s.sec + "</td><td class='l'>" +
           (m ? esc(m.unit.id + " " + m.unit.name + "　" + m.q.q) : ("seq " + s.seq)) +
           "</td></tr>";
    });
    h += "</table></div>";
  }
  $("resultStats").innerHTML = h;

  var wrong = res.filter(function(r){ return !r.ok; });
  var box = $("wrongList");
  if(!wrong.length){
    box.innerHTML = '<div class="banner info">間違いはありませんでした。</div>';
    $("btnRetryWrong").disabled = true;
  }else{
    $("btnRetryWrong").disabled = false;
    var w = '<h2>この回で間違えた問題（' + wrong.length + '問）</h2>';
    wrong.forEach(function(r){
      w += '<div class="wrong"><div class="small">' +
           esc(r.item.unit.id + " " + r.item.unit.name) + '</div><div class="q">' +
           esc(r.item.q.q) + '</div><div class="small">あなたの解答：' +
           esc(r.user || "（未回答）") + '</div><div>正解：' + esc(r.item.q.a) +
           '</div><div class="small">解説：' + esc(r.item.q.exp) + "</div></div>";
    });
    box.innerHTML = w;
  }
  $("btnNextRound").hidden = !(quiz.mode === "round" && completed);
  show("s-result");
}

/* ================= 間違いノートの表示・印刷 ================= */
function renderNoteView(){
  var list = noteItems("wrong");
  $("noteViewInfo").textContent = "現在 " + list.length + "問（よく間違える順）";
  var h = "";
  if(!list.length) h = '<div class="banner info">間違いノートは空です。</div>';
  list.forEach(function(x){
    h += '<div class="noteitem"><div class="hd"><span class="badge">' +
         x.entry.wrongCount + '回</span>' +
         esc(x.item.unit.id + " " + x.item.unit.name + "-" + x.item.q.no) +
         "　連続正解 " + x.entry.correctStreak + "</div>" +
         '<div class="q">' + esc(x.item.q.q) + "</div>" +
         "<div>正解：" + esc(x.item.q.a) + "</div>" +
         '<div class="small">解説：' + esc(x.item.q.exp) + "</div></div>";
  });
  $("noteList").innerHTML = h;
  show("s-note");
}
function renderPrint(){
  var list = noteItems("wrong");
  var d = new Date();
  var head = '<div class="printhead"><h2>間違いノート（' +
             d.getFullYear() + "年" + (d.getMonth()+1) + "月" + d.getDate() + "日時点・" +
             list.length + "問）</h2><div class='small'>" +
             esc(SUBJECT.subjectName) + "</div></div>";
  var h = "";
  list.forEach(function(x){
    h += '<div class="pq"><div class="hd"><span class="badge">' + x.entry.wrongCount +
         '回</span>' + esc(x.item.unit.id + " " + x.item.unit.name + "-" + x.item.q.no) +
         "</div>" +
         '<div class="q">' + esc(x.item.q.q) + "</div>" +
         '<div class="a">正解：' + esc(x.item.q.a) + "</div>" +
         '<div class="e">解説：' + esc(x.item.q.exp) + "</div>" +
         '<div class="chk">□□□</div></div>';
  });
  if(!list.length) h = "<p>間違いノートは空です。</p>";
  var foot = '<div class="printfoot">' + esc(location.href) + "　／　印刷日 " +
             d.getFullYear() + "-" + (d.getMonth()+1) + "-" + d.getDate() + "</div>";
  $("printArea").innerHTML = head + h + foot;
  show("s-print");
}

/* ================= 設定画面 ================= */
function renderSettings(){
  var s = settings();
  renderOptRow("optStreak",
    [{label:"1回", value:1},{label:"2回（既定）", value:2},{label:"3回", value:3}],
    s.graduateStreak, function(v){ s.graduateStreak = v; setDirty(true); renderSettings(); });
  renderOptRow("optDefCount",
    [{label:"10問", value:10},{label:"20問（既定）", value:20},{label:"30問", value:30}],
    s.defaultCount, function(v){ s.defaultCount = v; cfg.count = v; setDirty(true); renderSettings(); });
  var els = document.querySelectorAll("[data-automic]");
  for(var i=0;i<els.length;i++)
    els[i].setAttribute("aria-pressed",
      String((els[i].dataset.automic === "on") === !!s.autoMic));
  els = document.querySelectorAll("[data-fs]");
  for(i=0;i<els.length;i++)
    els[i].setAttribute("aria-pressed", String(els[i].dataset.fs === s.fontSize));
  applySettings();
  show("s-settings");
}
function applySettings(){
  document.body.classList.toggle("fs-large", settings().fontSize === "large");
}

/* ================= 中断と再開 ================= */
function pauseAndSave(){
  stopTimer();
  var data = {
    type: "resume", subjectId: SUBJECT.subjectId, mode: quiz.mode,
    round: quiz.round, units: pickedUnits().map(function(u){ return u.id; }),
    cfg: JSON.parse(JSON.stringify(cfg)),
    roundList: quiz.roundList.map(function(x){ return x.q.seq; }),
    queue: quiz.queue.map(function(x){ return x.q.seq; }),
    wrongPass: quiz.wrongPass.map(function(x){ return x.q.seq; }),
    done: quiz.done, elapsedSec: Math.round(sessionElapsed()),
    session: JSON.parse(JSON.stringify(session)), savedAt: nowIso()
  };
  download(fileBase() + "_resume.json", data);
  msgNote("中断した状態を保存しました（" + fileBase() + "_resume.json）。" +
          "ホームの「中断した周回を再開する」から続きを始められます。");
  show("s-home");
  renderHome();
}
function importResumeText(text){
  var d = JSON.parse(text);
  if(!d || d.type !== "resume") throw new Error("再開用のファイルではありません");
  function toItems(arr){
    var out = [];
    (arr||[]).forEach(function(sq){ if(SEQMAP[sq]) out.push(SEQMAP[sq]); });
    return out;
  }
  picked = {};
  (d.units||[]).forEach(function(u){ picked[u] = true; });
  cfg = Object.assign(cfg, d.cfg || {});
  session = Object.assign(newSession(d.mode, d.units || [], d.round || 1), d.session || {});
  session._t0 = Date.now();
  session._base = d.elapsedSec || 0;
  session._seen = (d.session && d.session._seen) || {};
  session._times = (d.session && d.session._times) || [];
  quiz = {mode:d.mode, roundList:toItems(d.roundList), queue:toItems(d.queue),
          wrongPass:toItems(d.wrongPass), round:d.round || 1, done:d.done || 0,
          results:[]};
  startTimer();
  nextQuestion();
  return {round:quiz.round, remain:quiz.queue.length + quiz.wrongPass.length};
}

/* ================= 開始の入口 ================= */
function startFromUnits(){
  ensureNote(function(){
    var pool = orderPool(filterPool());
    var units = pickedUnits().map(function(u){ return u.id; });
    if(cfg.mode !== "round" && cfg.count > 0) pool = pool.slice(0, cfg.count);
    lastPool = pool.slice();
    session = null;
    quiz = null;
    startQuiz(pool, cfg.mode, units, 1);
    quiz.results = [];
  });
}
function startFromNote(){
  ensureNote(function(){
    var list = noteItems(noteCfg.order).map(function(x){ return x.item; });
    if(noteCfg.count > 0) list = list.slice(0, noteCfg.count);
    if(!list.length) return;
    lastPool = list.slice();
    session = null;
    quiz = null;
    var units = [];
    list.forEach(function(x){ if(units.indexOf(x.unit.id) < 0) units.push(x.unit.id); });
    startQuiz(list, "normal", units, 1);
    quiz.results = [];
  });
}

/* ================= イベント ================= */
function bind(){
  $("btnGoUnit").addEventListener("click", function(){ renderUnits(); show("s-unit"); });
  $("btnUnitAll").addEventListener("click", function(){
    SUBJECT.units.forEach(function(u){ picked[u.id] = true; }); syncUnits();
  });
  $("btnUnitNone").addEventListener("click", function(){ picked = {}; syncUnits(); });
  $("btnUnitNext").addEventListener("click", openSetup);
  $("btnToHome1").addEventListener("click", function(){ renderHome(); show("s-home"); });
  ["mode","level","order"].forEach(function(k){
    document.querySelectorAll("[data-" + k + "]").forEach(function(b){
      b.addEventListener("click", function(){ cfg[k] = b.dataset[k]; syncOpts(); });
    });
  });
  $("btnStart").addEventListener("click", startFromUnits);
  $("btnBackUnit").addEventListener("click", function(){ show("s-unit"); });
  $("btnNoteQuiz").addEventListener("click", startFromNote);
  $("btnNoteView").addEventListener("click", renderNoteView);
  $("btnNoteSave").addEventListener("click", saveNote);
  $("btnNoteSave2").addEventListener("click", saveNote);
  $("btnResultSave").addEventListener("click", saveNote);
  $("btnLogSave").addEventListener("click", saveLog);
  $("btnSettings").addEventListener("click", renderSettings);
  $("btnNotePrint").addEventListener("click", renderPrint);
  $("btnPrintBack").addEventListener("click", renderNoteView);
  $("btnDoPrint").addEventListener("click", function(){ window.print(); });
  $("btnToHome3").addEventListener("click", function(){ renderHome(); show("s-home"); });
  $("btnToHome4").addEventListener("click", function(){ renderHome(); show("s-home"); });

  $("btnMic").addEventListener("click", function(){
    if(listening){ try{ rec.stop(); }catch(e){} } else { startMic(); }
  });
  $("btnKbd").addEventListener("click", function(){
    kbdSticky = true; $("kbdBox").hidden = false; $("kbdInput").focus();
  });
  $("btnKbdSubmit").addEventListener("click", function(){
    submitAnswer($("kbdInput").value.trim());
  });
  $("kbdInput").addEventListener("keydown", function(ev){
    if(ev.key === "Enter"){ ev.preventDefault(); submitAnswer($("kbdInput").value.trim()); }
  });
  $("btnSkip").addEventListener("click", function(){ submitAnswer(""); });
  $("btnPause").addEventListener("click", pauseAndSave);
  $("btnQuit").addEventListener("click", function(){
    stopTimer(); renderHome(); show("s-home");
  });
  $("btnSelfOk").addEventListener("click", function(){
    setVerdict(true); settle(true);
    $("selfButtons").hidden = true; nextQuestion();
  });
  $("btnSelfNg").addEventListener("click", function(){
    setVerdict(false); settle(false);
    $("selfButtons").hidden = true; nextQuestion();
  });
  $("btnNext").addEventListener("click", function(){ nextQuestion(); });
  $("btnRetryWrong").addEventListener("click", function(){
    var w = (quiz.results || []).filter(function(r){ return !r.ok; })
                                .map(function(r){ return r.item; });
    if(!w.length) return;
    var us = session ? session.units : [];
    session = null;
    startQuiz(w, "normal", us, 1);
    quiz.results = [];
  });
  $("btnAgain").addEventListener("click", function(){
    if(!lastPool.length) return;
    session = null;
    startQuiz(lastPool.slice(), cfg.mode, [], 1);
    quiz.results = [];
  });
  $("btnNextRound").addEventListener("click", function(){
    var next = quiz.round + 1;
    var list = cfg.order === "shuffle" ? shuffle(quiz.roundList.slice()) : quiz.roundList.slice();
    session = null;
    startQuiz(list, "round", [], next);
    quiz.results = [];
  });
  $("btnToHome2").addEventListener("click", function(){ renderHome(); show("s-home"); });
  $("confirmYes").addEventListener("click", function(){ closeConfirm(true); });
  $("confirmNo").addEventListener("click", function(){ closeConfirm(false); });

  document.querySelectorAll("[data-automic]").forEach(function(b){
    b.addEventListener("click", function(){
      settings().autoMic = (b.dataset.automic === "on"); setDirty(true); renderSettings();
    });
  });
  document.querySelectorAll("[data-fs]").forEach(function(b){
    b.addEventListener("click", function(){
      settings().fontSize = b.dataset.fs; setDirty(true); renderSettings();
    });
  });

  readFile($("notePick"), function(t){
    var r = importNoteText(t);
    msgNote("ノートを読み込みました：" + r.loaded + "問" +
            (r.ignored ? ("／現在の問題データに無い " + r.ignored + "件は無視しました") : ""));
  });
  readFile($("logPick"), function(t){
    var r = importLogText(t);
    msgNote("学習ログを読み込みました：" + r.sessions + "件");
  });
  readFile($("resumePick"), function(t){
    var r = importResumeText(t);
    msgNote("");
    void r;
  });

  window.addEventListener("beforeunload", function(e){
    if(!dirty) return;
    e.preventDefault();
    e.returnValue = "保存していない学習の記録があります。";
    return e.returnValue;
  });
  window.addEventListener("online", onNet);
  window.addEventListener("offline", onNet);
}
function onNet(){
  var off = navigatorOffline();
  var b = $("offlineBanner");
  b.hidden = !off;
  if(off){
    b.className = "banner";
    b.textContent = "オフラインです。問題を解くことはできますが、音声認識は使えません" +
                    "（キーボード入力に切り替わります）。";
  }
  if(!$("s-quiz").hidden) renderSpeechBanner();
}

/* ================= 起動 ================= */
bind();
onNet();
getJSON("subjects.json").then(function(d){
  SUBJECTS = (d && d.subjects) || [];
  renderSubjects();
  var on = SUBJECTS.filter(function(s){ return s.enabled; });
  if(on.length === 1) return openSubject(on[0]);   // 科目が1つなら自動で選ぶ
}).catch(function(e){
  showLoadError(String(e.message || e));
});

/* Service Worker（https でのみ有効。失敗しても動作に影響させない） */
if("serviceWorker" in navigator && location.protocol !== "file:"){
  window.addEventListener("load", function(){
    try{
      navigator.serviceWorker.register("sw.js").catch(function(){ /* 失敗は無視 */ });
    }catch(e){ /* 失敗は無視 */ }
  });
}

/* 動作確認用（機能には影響しない） */
window.__app = {
  norm:norm, judge:judge, isSelfCheck:isSelfCheck,
  getSubjects:function(){ return SUBJECTS; },
  getSubject:function(){ return SUBJECT; },
  getQuiz:function(){ return quiz; },
  getCfg:function(){ return cfg; },
  getNoteCfg:function(){ return noteCfg; },
  getPicked:function(){ return picked; },
  getNote:function(){ return note; },
  getLogs:function(){ return logs; },
  getSession:function(){ return session; },
  getSettings:settings,
  isDirty:function(){ return dirty; },
  setNoteAsked:function(v){ noteAsked = v; },
  importNoteText:importNoteText,
  importResumeText:importResumeText,
  exportNote:function(){ return JSON.parse(JSON.stringify(note)); },
  noteItems:noteItems,
  hasSR:function(){ return !!SR; },
  micLog:function(){ return window.__micLog; },
  forceBlocked:function(){ fallbackToKeyboard("テスト：マイクの利用が許可されませんでした。", true); }
};

