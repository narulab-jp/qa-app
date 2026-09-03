/* Service Worker
   キャッシュ優先・ネットワークはフォールバック。
   キャッシュ名にバージョンを持たせ、更新時に古いキャッシュを削除する。
   file:// では登録されない（app.js 側で判定している）。 */
"use strict";

var VERSION = "v14";
var CACHE = "qa-app-" + VERSION;

/* アプリの骨組み */
var CORE = [
  "./",
  "./index.html",
  "./app.css",
  "./app.js",
  "./subjects.json",
  "./manifest.json",
  "./icon.svg",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable.png"
];

/* subjects.json を読んで、有効な科目のデータと、そのデータが指す図版を
   まとめて取り込む。科目や図が増えても sw.js を書き換えずに済む。 */
function subjectFiles(){
  return fetch("./subjects.json", {cache: "no-cache"})
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(j){
      if(!j || !j.subjects) return [];
      var files = j.subjects.filter(function(s){ return s.enabled; })
                            .map(function(s){ return s.file; });
      return Promise.all(files.map(function(f){
        return fetch("./" + f, {cache: "no-cache"})
          .then(function(r){ return r.ok ? r.json() : null; })
          .then(function(d){
            var out = ["./" + f];
            if(!d || !d.units) return out;
            var seen = {};
            d.units.forEach(function(u){
              (u.questions || []).forEach(function(q){
                (q.figures || []).forEach(function(g){
                  if(!seen[g]){ seen[g] = 1; out.push("./" + g); }
                });
              });
            });
            return out;
          })
          .catch(function(){ return ["./" + f]; });
      })).then(function(lists){
        var all = [];
        lists.forEach(function(l){ all = all.concat(l); });
        return all;
      });
    })
    .catch(function(){ return []; });
}

self.addEventListener("install", function(ev){
  ev.waitUntil(
    caches.open(CACHE).then(function(c){
      /* 1つでも失敗したら全体が失敗する addAll は使わない */
      function addAll(list){
        return Promise.all(list.map(function(u){
          return c.add(u).catch(function(){ /* 個別の失敗は無視 */ });
        }));
      }
      return addAll(CORE).then(subjectFiles).then(addAll);
    }).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function(ev){
  ev.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){
        if(k !== CACHE) return caches.delete(k);   // 古いキャッシュを削除
      }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function(ev){
  var req = ev.request;
  if(req.method !== "GET") return;
  var url;
  try{ url = new URL(req.url); }catch(e){ return; }
  if(url.origin !== self.location.origin) return;   // 同一オリジンだけ扱う

  ev.respondWith(
    caches.match(req, {ignoreSearch: true}).then(function(hit){
      if(hit) return hit;                            // キャッシュ優先
      return fetch(req).then(function(res){
        if(res && res.ok && res.type === "basic"){
          var copy = res.clone();
          caches.open(CACHE).then(function(c){ c.put(req, copy); });
        }
        return res;
      }).catch(function(){
        /* オフラインで未キャッシュのときは、遷移要求だけ index.html を返す */
        if(req.mode === "navigate") return caches.match("./index.html");
        return new Response("", {status:504, statusText:"offline"});
      });
    })
  );
});
