/* 一問一答アプリ　ロジック
   科目に依存しない。表示する語はすべてデータ（subjects.json / 科目JSON）から取る。
   判定ロジック（norm / judge）は試作で動作確認済みのものをそのまま使っている。 */
"use strict";

/* ---------------- 状態 ---------------- */
var SUBJECTS = [];        // subjects.json の中身
var SUBJECT = null;       // 選択中の科目データ
var picked = {};          // 選んだ単元 id → true
var cfg = {count:10, level:"SA", order:"shuffle"};
var quiz = {list:[], idx:0, results:[]};
var lastPool = [];        // 「同じ範囲でもう一度」用
var current = null, currentUser = "";
var rec = null, listening = false, speechBlocked = false, kbdSticky = false;
var SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
var COUNTS = [5, 10, 20, 0];   // 0 = すべて

window.__micLog = [];     /* 動作確認用の記録（機能には影響しない） */

function $(id){ return document.getElementById(id); }
function show(id){
  ["s-subject","s-unit","s-setup","s-quiz","s-judge","s-result"].forEach(function(s){
    $(s).hidden = (s !== id);
  });
  window.scrollTo(0,0);
}
function esc(s){
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function label(){ return (SUBJECT && SUBJECT.unitLabel) || "単元"; }

/* ---------------- 表記ゆれの正規化（試作と同一） ---------------- */
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

/* ---------------- 自動判定（試作と同一） ---------------- */
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

/* ---------------- 読み込み ---------------- */
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

/* ---------------- 科目 ---------------- */
function renderSubjects(){
  var box = $("subjectList");
  box.innerHTML = "";
  SUBJECTS.forEach(function(s){
    var b = document.createElement("button");
    b.className = "btn";
    b.id = "subj-" + s.id;
    b.disabled = !s.enabled;
    b.textContent = s.name + (s.enabled ? "" : "　― 準備中");
    if(s.enabled) b.addEventListener("click", function(){ openSubject(s); });
    box.appendChild(b);
  });
  if(!SUBJECTS.length){
    box.innerHTML = '<div class="banner">科目が登録されていません。' +
                    'subjects.json をご確認ください。</div>';
  }
}
function openSubject(s){
  getJSON(s.file).then(function(d){
    SUBJECT = d;
    picked = {};
    renderUnits();
    show("s-unit");
  }).catch(function(e){
    show("s-subject");
    showLoadError(String(e.message || e));
  });
}

/* ---------------- 単元 ---------------- */
function renderUnits(){
  $("unitTitle").textContent = SUBJECT.subjectName;
  $("unitLead").textContent =
    "出題する" + label() + "を選んでください（いくつでも選べます）。";
  var box = $("unitList");
  box.innerHTML = "";
  SUBJECT.units.forEach(function(u){
    var b = document.createElement("button");
    b.className = "unit";
    b.id = "unit-" + u.id;
    b.setAttribute("aria-pressed","false");
    b.innerHTML = '<span class="mark"></span>' +
                  '<span class="nm">' + esc(u.id + " " + u.name) + '</span>' +
                  '<span class="ct">' + u.questions.length + "問</span>";
    b.addEventListener("click", function(){
      picked[u.id] = !picked[u.id];
      syncUnits();
    });
    box.appendChild(b);
  });
  syncUnits();
}
function syncUnits(){
  var n = 0, q = 0;
  SUBJECT.units.forEach(function(u){
    var on = !!picked[u.id];
    var el = $("unit-" + u.id);
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

/* ---------------- 設定 ---------------- */
function renderCountOptions(){
  var box = $("optCount");
  box.innerHTML = "";
  COUNTS.forEach(function(c){
    var b = document.createElement("button");
    b.className = "opt";
    b.dataset.count = String(c);
    b.textContent = c === 0 ? "選んだ範囲すべて" : (c + "問ずつ");
    b.addEventListener("click", function(){ cfg.count = c; syncOpts(); });
    box.appendChild(b);
  });
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
  var i, els;
  els = document.querySelectorAll("[data-count]");
  for(i=0;i<els.length;i++)
    els[i].setAttribute("aria-pressed", String(Number(els[i].dataset.count) === cfg.count));
  els = document.querySelectorAll("[data-level]");
  for(i=0;i<els.length;i++)
    els[i].setAttribute("aria-pressed", String(els[i].dataset.level === cfg.level));
  els = document.querySelectorAll("[data-order]");
  for(i=0;i<els.length;i++)
    els[i].setAttribute("aria-pressed", String(els[i].dataset.order === cfg.order));
  var pool = filterPool();
  var n = cfg.count === 0 ? pool.length : Math.min(cfg.count, pool.length);
  $("setupCount").textContent =
    "この設定での出題数：" + n + "問（対象 " + pool.length + "問中）";
  $("btnStart").disabled = (pool.length === 0);
}
function filterPool(){
  var out = [];
  pickedUnits().forEach(function(u){
    u.questions.forEach(function(q){
      if(cfg.level === "ALL" || q.level === "S" || q.level === "A"){
        out.push({q:q, unit:u});
      }
    });
  });
  return out;
}
function buildAndStart(){
  var pool = filterPool();
  if(cfg.order === "shuffle"){
    for(var i=pool.length-1;i>0;i--){
      var j = Math.floor(Math.random()*(i+1));
      var t = pool[i]; pool[i] = pool[j]; pool[j] = t;
    }
  }else{
    pool.sort(function(a,b){
      if(a.unit.id !== b.unit.id) return a.unit.id < b.unit.id ? -1 : 1;
      return a.q.no - b.q.no;
    });
  }
  if(cfg.count > 0) pool = pool.slice(0, cfg.count);
  lastPool = pool.slice();
  startQuiz(pool);
}
function startQuiz(list){
  quiz = {list:list, idx:0, results:[]};
  nextQuestion();
}

/* ---------------- 出題 ---------------- */
function nextQuestion(){
  if(quiz.idx >= quiz.list.length){ showResult(); return; }
  var item = quiz.list[quiz.idx];
  current = item.q;
  currentUser = "";
  $("mProgress").textContent = (quiz.idx+1) + " / " + quiz.list.length + "問目";
  $("mUnit").textContent = item.unit.id + " " + item.unit.name + " 節" + current.section;
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
  renderSpeechBanner();
  show("s-quiz");
  if(!$("kbdBox").hidden) $("kbdInput").focus();
}
function renderSpeechBanner(){
  var b = $("speechBanner");
  if(!SR){
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
  if(!text){
    h.textContent = "ここに聞き取った内容が表示されます";
    h.className = "heard empty";
  }else{
    h.textContent = interim ? (text + " …") : text;
    h.className = "heard";
  }
}

/* ---------------- 音声認識 ---------------- */
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
    }else{
      stopMicUI();
    }
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

/* ---------------- 判定 ---------------- */
function submitAnswer(text){
  if(listening && rec){ try{ rec.stop(); }catch(e){} }
  currentUser = text || "";
  var self = isSelfCheck(current);
  $("jUser").textContent = currentUser ? currentUser : "（未回答）";
  $("jAns").textContent = current.a;
  $("jExp").textContent = current.exp;
  $("jAnsLbl").textContent = self ? "模範解答" : "正解";
  $("judgeSelfNote").hidden = !self;
  if(self && currentUser){
    $("verdict").hidden = true;
    $("selfButtons").hidden = false;
    $("btnNext").hidden = true;
  }else{
    var ok = currentUser ? judge(currentUser, current) : false;
    setVerdict(ok);
    $("selfButtons").hidden = true;
    $("btnNext").hidden = false;
    record(ok);
  }
  show("s-judge");
}
function setVerdict(ok){
  var v = $("verdict");
  v.hidden = false;
  v.textContent = ok ? "○" : "×";
  v.className = "verdict " + (ok ? "ok" : "ng");
}
function record(ok){
  quiz.results.push({item:quiz.list[quiz.idx], user:currentUser, ok:ok});
}

/* ---------------- 結果 ---------------- */
function showResult(){
  var ok = quiz.results.filter(function(r){ return r.ok; }).length;
  $("score").textContent = "正答 " + ok + " / " + quiz.results.length + " 問";
  var wrong = quiz.results.filter(function(r){ return !r.ok; });
  var box = $("wrongList");
  if(!wrong.length){
    box.innerHTML = '<div class="banner info">全問正解です。</div>';
    $("btnRetryWrong").disabled = true;
  }else{
    $("btnRetryWrong").disabled = false;
    var html = '<h2>間違えた問題（' + wrong.length + '問）</h2>';
    wrong.forEach(function(r){
      html += '<div class="wrong">' +
              '<div class="small">' + esc(r.item.unit.id + " " + r.item.unit.name) + '</div>' +
              '<div class="q">' + esc(r.item.q.q) + '</div>' +
              '<div class="small">あなたの解答：' + esc(r.user || "（未回答）") + '</div>' +
              '<div>正解：' + esc(r.item.q.a) + '</div>' +
              '<div class="small">解説：' + esc(r.item.q.exp) + '</div></div>';
    });
    box.innerHTML = html;
  }
  show("s-result");
}

/* ---------------- イベント ---------------- */
function bind(){
  $("btnUnitAll").addEventListener("click", function(){
    SUBJECT.units.forEach(function(u){ picked[u.id] = true; }); syncUnits();
  });
  $("btnUnitNone").addEventListener("click", function(){ picked = {}; syncUnits(); });
  $("btnUnitNext").addEventListener("click", openSetup);
  $("btnToSubject").addEventListener("click", function(){ show("s-subject"); });
  document.querySelectorAll("[data-level]").forEach(function(b){
    b.addEventListener("click", function(){ cfg.level = b.dataset.level; syncOpts(); });
  });
  document.querySelectorAll("[data-order]").forEach(function(b){
    b.addEventListener("click", function(){ cfg.order = b.dataset.order; syncOpts(); });
  });
  $("btnStart").addEventListener("click", buildAndStart);
  $("btnBackUnit").addEventListener("click", function(){ show("s-unit"); });
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
  $("btnQuit").addEventListener("click", function(){ show("s-unit"); });
  $("btnSelfOk").addEventListener("click", function(){
    setVerdict(true); record(true);
    $("selfButtons").hidden = true; quiz.idx++; nextQuestion();
  });
  $("btnSelfNg").addEventListener("click", function(){
    setVerdict(false); record(false);
    $("selfButtons").hidden = true; quiz.idx++; nextQuestion();
  });
  $("btnNext").addEventListener("click", function(){ quiz.idx++; nextQuestion(); });
  $("btnRetryWrong").addEventListener("click", function(){
    var w = quiz.results.filter(function(r){ return !r.ok; })
                        .map(function(r){ return r.item; });
    if(w.length) startQuiz(w);
  });
  $("btnAgain").addEventListener("click", function(){
    if(lastPool.length) startQuiz(lastPool.slice());
  });
  $("btnToUnit").addEventListener("click", function(){ show("s-unit"); });
}

/* ---------------- 起動 ---------------- */
bind();
renderCountOptions();
getJSON("subjects.json").then(function(d){
  SUBJECTS = (d && d.subjects) || [];
  renderSubjects();
  var on = SUBJECTS.filter(function(s){ return s.enabled; });
  if(on.length === 1) openSubject(on[0]);   // 科目が1つなら自動で単元一覧へ
}).catch(function(e){
  showLoadError(String(e.message || e));
});

/* 動作確認用（機能には影響しない） */
window.__app = {
  norm:norm, judge:judge, isSelfCheck:isSelfCheck,
  getSubjects:function(){ return SUBJECTS; },
  getSubject:function(){ return SUBJECT; },
  getQuiz:function(){ return quiz; },
  getCfg:function(){ return cfg; },
  getPicked:function(){ return picked; },
  hasSR:function(){ return !!SR; },
  micLog:function(){ return window.__micLog; },
  forceBlocked:function(){ fallbackToKeyboard("テスト：マイクの利用が許可されませんでした。", true); }
};
