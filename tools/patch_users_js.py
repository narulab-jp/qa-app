# -*- coding: utf-8 -*-
"""指示C（複数利用者対応）のための app.js パッチ。
既存の判定ロジック（norm / judge）と間違いノートの出入りの規則は変更しない。"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "app.js")
t = io.open(P, encoding="utf-8-sig").read().replace("\r\n", "\n")
ok = True


def sub(old, new, tag):
    global t, ok
    if old not in t:
        print("★未検出: %s" % tag)
        ok = False
        return
    t = t.replace(old, new, 1)


# ---------------------------------------------------------------- 状態
sub("""var note = null;        // 間違いノート
var noteLoaded = false; // ファイルから読み込んだか
var noteAsked = false;  // 「ノートなしで始めますか」を尋ねたか
var logs = null;        // 学習ログ
var dirty = false;      // 未保存の変更があるか""",
"""var users = [];         // 利用者名の一覧（人数の上限は設けない）
var currentUser = null; // 現在の利用者名。null の間は学習を始められない
var notes = {};         // 利用者名 → 間違いノート
var logsMap = {};       // 利用者名 → 学習ログ

var note = null;        // 現在の利用者の間違いノート
var noteLoaded = false; // ファイルから読み込んだか
var noteAsked = false;  // 「ノートなしで始めますか」を尋ねたか
var logs = null;        // 現在の利用者の学習ログ
var dirty = false;      // 未保存の変更があるか""", "状態")

# ---------------------------------------------------------------- show()
sub("""function show(id){
  ["s-home","s-unit","s-setup","s-quiz","s-judge","s-result","s-note",
   "s-settings","s-print"].forEach(function(s){ $(s).hidden = (s !== id); });
  window.scrollTo(0,0);
}""",
"""function show(id){
  ["s-user","s-home","s-unit","s-setup","s-quiz","s-judge","s-result","s-note",
   "s-settings","s-print"].forEach(function(s){ $(s).hidden = (s !== id); });
  renderUserBar(id);
  window.scrollTo(0,0);
}""", "show")

# ---------------------------------------------------------------- newNote
sub("""function newNote(){
  return {subjectId:(SUBJECT?SUBJECT.subjectId:null), updated:nowIso(),
          entries:[], history:[], settings:JSON.parse(JSON.stringify(DEFAULT_SETTINGS))};
}""",
"""function newNote(user){
  return {user:(user || currentUser), users:users.slice(),
          subjectId:(SUBJECT?SUBJECT.subjectId:null), updated:nowIso(),
          entries:[], history:[], settings:JSON.parse(JSON.stringify(DEFAULT_SETTINGS))};
}""", "newNote")

# ---------------------------------------------------------------- newLogs / session
sub("""function newLogs(){ return {subjectId:(SUBJECT?SUBJECT.subjectId:null), sessions:[]}; }""",
    """function newLogs(user){
  return {user:(user || currentUser), subjectId:(SUBJECT?SUBJECT.subjectId:null),
          sessions:[]};
}""", "newLogs")
sub("""    subjectId: SUBJECT.subjectId, mode: mode, units: units, round: round || 1,""",
    """    user: currentUser,
    subjectId: SUBJECT.subjectId, mode: mode, units: units, round: round || 1,""",
    "session に user")

# ---------------------------------------------------------------- 利用者の管理
sub("""/* ================= ファイルの保存・読み込み ================= */""",
"""/* ================= 利用者の管理 ================= */
/* ログインもパスワードも設けない。家庭内で使うため、名前で切り替えるだけにする。 */
function normUserName(s){ return String(s || "").trim(); }
function hasUser(n){ return users.indexOf(n) >= 0; }
function ensureUser(n){
  n = normUserName(n);
  if(n && !hasUser(n)) users.push(n);
  return n;
}
function stash(){                     /* 現在の利用者の記録を控える */
  if(currentUser){ notes[currentUser] = note; logsMap[currentUser] = logs; }
}
function setCurrentUser(n){
  n = normUserName(n);
  if(!n) return false;
  stash();
  ensureUser(n);
  currentUser = n;
  note = notes[n] || newNote(n);
  logs = logsMap[n] || newLogs(n);
  note.user = n;
  logs.user = n;
  notes[n] = note;
  logsMap[n] = logs;
  noteLoaded = !!note._loaded;
  noteAsked = noteLoaded;
  applySettings();
  return true;
}
function addUser(n){
  n = normUserName(n);
  if(!n) return {ok:false, msg:"名前を入れてください。"};
  if(hasUser(n)) return {ok:false, msg:"「" + n + "」はすでに登録されています。"};
  users.push(n);
  setCurrentUser(n);
  setDirty(true);
  return {ok:true, msg:"「" + n + "」を追加しました。"};
}
function renameUser(oldName, newName){
  newName = normUserName(newName);
  if(!newName) return {ok:false, msg:"名前を入れてください。"};
  if(newName !== oldName && hasUser(newName))
    return {ok:false, msg:"「" + newName + "」はすでに登録されています。"};
  var i = users.indexOf(oldName);
  if(i < 0) return {ok:false, msg:"見つかりません。"};
  users[i] = newName;
  if(notes[oldName]){ notes[newName] = notes[oldName]; notes[newName].user = newName;
                      delete notes[oldName]; }
  if(logsMap[oldName]){ logsMap[newName] = logsMap[oldName]; logsMap[newName].user = newName;
                        delete logsMap[oldName]; }
  if(currentUser === oldName){ currentUser = newName; if(note) note.user = newName;
                               if(logs) logs.user = newName; }
  setDirty(true);
  return {ok:true, msg:"「" + oldName + "」を「" + newName + "」に変えました。"};
}
function deleteUser(n){
  var i = users.indexOf(n);
  if(i < 0) return {ok:false, msg:"見つかりません。"};
  users.splice(i, 1);
  delete notes[n];
  delete logsMap[n];
  if(currentUser === n){
    currentUser = null; note = null; logs = null; noteLoaded = false; noteAsked = false;
    if(users.length === 1) setCurrentUser(users[0]);
  }
  setDirty(true);
  return {ok:true, msg:"「" + n + "」を削除しました。"};
}
/* 一覧から復元する（ノートに同梱された利用者一覧を取り込む） */
function mergeUsers(list){
  var added = 0;
  (list || []).forEach(function(n){
    n = normUserName(n);
    if(n && !hasUser(n)){ users.push(n); added++; }
  });
  return added;
}

var renaming = null;
function renderUserBar(screen){
  var bar = $("userBar");
  if(!currentUser || screen === "s-user" || screen === "s-print"){
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  $("userBarName").textContent = currentUser + " として学習中";
}
function renderUsers(){
  var box = $("userList");
  box.innerHTML = "";
  $("userLead").textContent = users.length
    ? "誰が使いますか。" : "はじめに、使う人の名前を登録してください。";
  users.forEach(function(n){
    var row = document.createElement("div");
    row.className = "userrow";
    row.id = "userrow-" + n;
    if(renaming === n){
      var inp = document.createElement("input");
      inp.className = "renameInput";
      inp.id = "renameInput";
      inp.value = n;
      var okb = document.createElement("button");
      okb.className = "icobtn"; okb.id = "btnRenameOk"; okb.textContent = "決定";
      var cab = document.createElement("button");
      cab.className = "icobtn"; cab.id = "btnRenameCancel"; cab.textContent = "やめる";
      okb.addEventListener("click", function(){
        var r = renameUser(n, $("renameInput").value);
        $("userMsg").textContent = r.msg;
        if(r.ok) renaming = null;
        renderUsers();
      });
      cab.addEventListener("click", function(){ renaming = null; renderUsers(); });
      row.appendChild(inp); row.appendChild(okb); row.appendChild(cab);
    }else{
      var b = document.createElement("button");
      b.className = "nmbtn";
      b.id = "user-" + n;
      b.textContent = n + (n === currentUser ? "　（いま選択中）" : "");
      b.setAttribute("aria-pressed", String(n === currentUser));
      b.addEventListener("click", function(){ pickUser(n); });
      var e = document.createElement("button");
      e.className = "icobtn"; e.id = "rename-" + n; e.textContent = "名前";
      e.addEventListener("click", function(){ renaming = n; renderUsers(); });
      var d = document.createElement("button");
      d.className = "icobtn"; d.id = "del-" + n; d.textContent = "削除";
      d.addEventListener("click", function(){
        askChoice("「" + n + "」を削除しますか。この人の記録もアプリから消えます。" +
                  "（保存したファイルは残ります）", "削除する", "やめる", function(yes){
          if(!yes) return;
          var r = deleteUser(n);
          $("userMsg").textContent = r.msg;
          renderUsers();
          if(currentUser) enterHome();
        });
      });
      row.appendChild(b); row.appendChild(e); row.appendChild(d);
    }
    box.appendChild(row);
  });
}
function pickUser(n){
  setCurrentUser(n);
  $("userMsg").textContent = "";
  enterHome();
}
function enterHome(){
  renderSubjects();
  renderHome();
  show("s-home");
}
/* 利用者が決まっていなければ選択画面へ。1人だけなら自動で選ぶ。 */
function gateUser(){
  if(currentUser){ enterHome(); return; }
  if(users.length === 1){ setCurrentUser(users[0]); enterHome(); return; }
  renderUsers();
  show("s-user");
}
function switchUser(){
  var go = function(){
    stash();
    renaming = null;
    renderUsers();
    show("s-user");
  };
  if(quiz && !$("s-quiz").hidden){
    askChoice("学習中です。中断して利用者を切り替えますか。",
              "切り替える", "やめる", function(yes){ if(yes){ stopTimer(); go(); } });
  }else{ go(); }
}

/* ================= ファイルの保存・読み込み ================= */""", "利用者の管理")

# ---------------------------------------------------------------- ファイル名
sub("""function fileBase(){ return (SUBJECT && SUBJECT.subjectId) || "subject"; }
function saveNote(){
  download(fileBase() + "_note.json", note);
  setDirty(false);
  msgNote("ノートを保存しました（" + fileBase() + "_note.json）");
  renderHome();
}
function saveLog(){
  download(fileBase() + "_log.json", logs);
  msgNote("学習ログを保存しました（" + fileBase() + "_log.json）");
}""",
"""function fileBase(){ return (SUBJECT && SUBJECT.subjectId) || "subject"; }
/* ファイル名に使えない文字はアンダースコアに置き換える。表示名はそのまま保つ。 */
function safeName(s){ return String(s || "").replace(/[\\\\\\/:*?"<>|\\s]/g, "_"); }
function noteFileName(){ return fileBase() + "_note_" + safeName(currentUser) + ".json"; }
function logFileName(){ return fileBase() + "_log_" + safeName(currentUser) + ".json"; }
function resumeFileName(){ return fileBase() + "_resume_" + safeName(currentUser) + ".json"; }
function saveNote(){
  note.user = currentUser;
  note.users = users.slice();          /* 利用者の一覧も一緒に保存する */
  download(noteFileName(), note);
  setDirty(false);
  msgNote("ノートを保存しました（" + noteFileName() + "）");
  renderHome();
}
function saveLog(){
  logs.user = currentUser;
  download(logFileName(), logs);
  msgNote("学習ログを保存しました（" + logFileName() + "）");
}""", "ファイル名")

# ---------------------------------------------------------------- ノート読み込み
sub("""/* 読み込み時の照合：現在の問題データに無い seq は無視し、件数を表示する */
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
}""",
"""/* 読み込み時の照合：現在の問題データに無い seq は無視し、件数を表示する */
function applyNote(d){
  var kept = [], ignored = 0;
  d.entries.forEach(function(e){
    if(SEQMAP[e.seq]) kept.push(e); else ignored++;
  });
  var addedUsers = mergeUsers(d.users);
  note = {
    user: currentUser,
    users: users.slice(),
    subjectId: d.subjectId || (SUBJECT ? SUBJECT.subjectId : null),
    updated: d.updated || nowIso(),
    entries: kept,
    history: Array.isArray(d.history) ? d.history : [],
    settings: Object.assign(JSON.parse(JSON.stringify(DEFAULT_SETTINGS)), d.settings || {}),
    _loaded: true
  };
  notes[currentUser] = note;
  noteLoaded = true;
  noteAsked = true;
  setDirty(false);
  applySettings();
  renderUsers();
  renderHome();
  return {loaded: kept.length, ignored: ignored, addedUsers: addedUsers,
          legacy: !d.user, owner: d.user || null};
}
function noteLoadMessage(r){
  var s = "ノートを読み込みました：" + r.loaded + "問";
  if(r.ignored) s += "／現在の問題データに無い " + r.ignored + "件は無視しました";
  if(r.addedUsers) s += "／利用者 " + r.addedUsers + "人を一覧に追加しました";
  if(r.legacy) s += "。利用者名の入っていない古い形式のファイルのため、「" +
                    currentUser + "」のものとして読み込みました。";
  return s;
}
/* 別人のノートは黙って読み込まない。必ず確認する。 */
function handleNoteLoad(d){
  if(!d || !Array.isArray(d.entries)) { msgNote("ノートの形式が違います。"); return null; }
  var owner = d.user ? normUserName(d.user) : null;
  if(owner && currentUser && owner !== currentUser){
    askChoice("このノートは「" + owner + "」のものです。今は「" + currentUser +
              "」として使っています。読み込みますか。",
              owner + "に切り替えて読み込む", "いいえ（戻る）", function(yes){
      if(!yes){ msgNote("読み込みませんでした。記録はそのままです。"); return; }
      mergeUsers(d.users);
      setCurrentUser(owner);
      var r = applyNote(d);
      msgNote("「" + owner + "」に切り替えました。" + noteLoadMessage(r));
      if(!$("s-user").hidden) enterHome();
    });
    return {pending:true, owner:owner};
  }
  if(!currentUser){
    mergeUsers(d.users);
    setCurrentUser(owner || (users.length ? users[0] : "利用者1"));
  }
  var r = applyNote(d);
  msgNote(noteLoadMessage(r));
  return r;
}
function importNoteText(text){
  var d = JSON.parse(text);
  return handleNoteLoad(d);
}""", "ノート読み込み")

# ---------------------------------------------------------------- ログ・再開
sub("""function importLogText(text){
  var d = JSON.parse(text);
  if(!d || !Array.isArray(d.sessions)) throw new Error("学習ログの形式が違います");
  logs = {subjectId: d.subjectId || fileBase(), sessions: d.sessions};
  renderHome();
  return {sessions: logs.sessions.length};
}""",
"""function importLogText(text){
  var d = JSON.parse(text);
  if(!d || !Array.isArray(d.sessions)) throw new Error("学習ログの形式が違います");
  logs = {user: currentUser, subjectId: d.subjectId || fileBase(), sessions: d.sessions};
  logsMap[currentUser] = logs;
  renderHome();
  return {sessions: logs.sessions.length, owner: d.user || null};
}""", "importLogText")

sub("""    type: "resume", subjectId: SUBJECT.subjectId, mode: quiz.mode,""",
    """    type: "resume", user: currentUser, subjectId: SUBJECT.subjectId, mode: quiz.mode,""",
    "resume に user")
sub("""  download(fileBase() + "_resume.json", data);
  msgNote("中断した状態を保存しました（" + fileBase() + "_resume.json）。" +""",
    """  download(resumeFileName(), data);
  msgNote("中断した状態を保存しました（" + resumeFileName() + "）。" +""",
    "resume ファイル名")

# ---------------------------------------------------------------- 確認ダイアログ
sub("""var confirmCb = null;
function askConfirm(msg, cb){
  $("confirmMsg").textContent = msg;
  $("confirmWrap").hidden = false;
  confirmCb = cb;
}""",
"""var confirmCb = null;
function askConfirm(msg, cb){ askChoice(msg, "はい", "いいえ", cb); }
function askChoice(msg, yesLabel, noLabel, cb){
  $("confirmMsg").textContent = msg;
  $("confirmYes").textContent = yesLabel || "はい";
  $("confirmNo").textContent = noLabel || "いいえ";
  $("confirmWrap").hidden = false;
  confirmCb = cb;
}""", "askChoice")

# ---------------------------------------------------------------- 科目の読み込み後
sub("""    picked = {};
    if(!note) note = newNote();
    if(!logs) logs = newLogs();
    note.subjectId = d.subjectId;
    logs.subjectId = d.subjectId;
    cfg.count = settings().defaultCount;
    renderSubjects();
    renderHome();
    show("s-home");""",
"""    picked = {};
    if(currentUser){
      if(!note) note = newNote();
      if(!logs) logs = newLogs();
      note.subjectId = d.subjectId;
      logs.subjectId = d.subjectId;
      cfg.count = settings().defaultCount;
    }
    renderSubjects();
    gateUser();""", "openSubject")

# ---------------------------------------------------------------- renderHome
sub("""function renderHome(){
  if(!SUBJECT) return;
  onNet();                     /* オンライン/オフラインの表示を最新にする */""",
"""function renderHome(){
  if(!SUBJECT || !currentUser || !note) return;
  onNet();                     /* オンライン/オフラインの表示を最新にする */""",
    "renderHome ガード")

# ---------------------------------------------------------------- イベント
sub("""  $("confirmYes").addEventListener("click", function(){ closeConfirm(true); });
  $("confirmNo").addEventListener("click", function(){ closeConfirm(false); });""",
"""  $("confirmYes").addEventListener("click", function(){ closeConfirm(true); });
  $("confirmNo").addEventListener("click", function(){ closeConfirm(false); });
  $("btnSwitchUser").addEventListener("click", switchUser);
  $("btnAddUser").addEventListener("click", function(){
    var r = addUser($("newUserName").value);
    $("userMsg").textContent = r.msg;
    if(r.ok){ $("newUserName").value = ""; renderUsers(); enterHome(); }
  });
  $("newUserName").addEventListener("keydown", function(ev){
    if(ev.key === "Enter"){ ev.preventDefault(); $("btnAddUser").click(); }
  });""", "利用者のイベント")

sub("""  readFile($("notePick"), function(t){
    var r = importNoteText(t);
    msgNote("ノートを読み込みました：" + r.loaded + "問" +
            (r.ignored ? ("／現在の問題データに無い " + r.ignored + "件は無視しました") : ""));
  });""",
"""  readFile($("notePick"), function(t){ importNoteText(t); });
  readFile($("userNotePick"), function(t){ importNoteText(t); });""", "notePick")

# ---------------------------------------------------------------- 起動
sub("""  var on = SUBJECTS.filter(function(s){ return s.enabled; });
  if(on.length === 1) return openSubject(on[0]);   // 科目が1つなら自動で選ぶ""",
"""  var on = SUBJECTS.filter(function(s){ return s.enabled; });
  if(on.length === 1) return openSubject(on[0]);   // 科目が1つなら自動で選ぶ
  gateUser();""", "起動")

# ---------------------------------------------------------------- __app
sub("""  getNote:function(){ return note; },
  getLogs:function(){ return logs; },""",
"""  getNote:function(){ return note; },
  getLogs:function(){ return logs; },
  getUsers:function(){ return users; },
  getCurrentUser:function(){ return currentUser; },
  getAllNotes:function(){ stash(); return notes; },
  addUser:addUser, renameUser:renameUser, deleteUser:deleteUser,
  setUser:setCurrentUser, switchUser:switchUser,
  noteFileName:noteFileName, logFileName:logFileName, safeName:safeName,""",
    "__app 追加")

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("app.js パッチ: %s" % ("すべて成功" if ok else "★未検出あり"))
sys.exit(0 if ok else 1)
