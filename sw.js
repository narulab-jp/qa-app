/* Service Worker
   キャッシュ優先・ネットワークはフォールバック。
   キャッシュ名にバージョンを持たせ、更新時に古いキャッシュを削除する。
   file:// では登録されない（app.js 側で判定している）。 */
"use strict";

var VERSION = "v1";
var CACHE = "qa-app-" + VERSION;

/* アプリの骨組み。科目データは実行時キャッシュで拾う（科目が増えても書き換え不要） */
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

self.addEventListener("install", function(ev){
  ev.waitUntil(
    caches.open(CACHE).then(function(c){
      /* 1つでも失敗したら全体が失敗する addAll は使わない */
      return Promise.all(CORE.map(function(u){
        return c.add(u).catch(function(){ /* 個別の失敗は無視 */ });
      }));
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
    caches.match(req).then(function(hit){
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
