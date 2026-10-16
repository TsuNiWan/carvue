# 新版驗證紀錄

本次素材版本 1.1.0；舊版通過結果僅作歷史背景。本文件只把實際執行且留有結果的項目列為通過。

| 項目 | 目前結果 |
| --- | --- |
| TypeScript | 通過 |
| 單元測試 | 87／87 通過 |
| 去品牌 GLB／可編輯來源 | 五款重建、八方位及開啟畫面審查完成 |
| 素材／公開契約 | 全部通過；150 個實際 GLB 反向案例通過 |
| Chrome／Edge 四桌機環境 | 170 項通過、78 項依範圍跳過，無未解決失敗 |
| 五車冷載／30 秒效能 | 全部通過，數據見下表 |
| 20 次切車／30 分鐘長測 | 四種桌機環境切車通過；獨立長測 30 分 3 秒、419 次循環通過 |
| 正式產物根目錄／子路徑 | 通過：62 次資源檢查、9 條旅程、37 組版面檢查，無錯誤 |
| 乾淨 clone／GitHub CI | 本機副本 87 項測試通過；GitHub 公開 clone 安裝、建置、啟動與歷史掃描通過，CI／Pages 成功 |
| 公開網站 | 五車直達、四門及後廂、返回總覽通過；9 份資源內容比對一致，無頁面或 HTTP 錯誤 |

## 重現命令

npm run typecheck、npm test、npm run validate:assets、npm run validate:public、npm run test:rigs、npm run build。npm run test:e2e 跑四種桌機環境；npm run test:soak 獨立執行 30 分鐘長測。正式產物檢查使用 node scripts/verification/verify-production.mjs carvue-production --final。

沙箱若無法建立系統暫存檔，可將 TEMP 與 TMP 指向專案內 node_modules/.cache/carvue-review-temp 後重試；不需更動產品邏輯。

30 分鐘長測用於正式發布前確認反覆操作的資源穩定性，或在模型載入、資源釋放、動畫迴圈有變更時重驗。README、文案與文件變更不觸發長測；應只執行連結、內容及發布檔案檢查。長測使用獨立 5180 埠，由 Playwright 啟停伺服器，保留逐次資源量測與錯誤紀錄，不錄製完整 trace。

效能門檻：每車 ≤12MiB；25Mbps／80ms 冷載可操作 ≤8秒；固定 DPR 上限 1.5、1920×1080 下測量 30 秒平均 ≥45FPS、p95 幀間隔 ≤50ms。硬體、瀏覽器及原始數據隨測試紀錄保存，不能泛化到未測試裝置。

## 實機量測

Windows 核心版本 10.0.26300、Intel Core i7-8700K、32 GiB 記憶體、NVIDIA GeForce RTX 2080 SUPER；Chrome 155.0.8059.85、Edge 155.0.4283.60。效能固定 1920×1080、實際 DPR 1（產品上限 1.5），以 headless Chrome 執行，每種工作負載各 30 秒。

| 車款 | GLB MiB | 冷載秒數 | 混合操作 FPS | 拖曳 FPS | 兩種工作負載 p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| sedan-01 | 4.89 | 4.73 | 178.10 | 178.98 | 5.70 |
| suv-01 | 10.63 | 7.00 | 178.26 | 176.98 | 5.70 |
| sedan-02 | 5.31 | 5.52 | 180.11 | 180.46 | 5.70 |
| suv-02 | 7.10 | 6.45 | 179.84 | 177.55 | 5.70 |
| sedan-03 | 7.94 | 6.56 | 177.46 | 178.25 | 5.70 |

冷載使用 25Mbps、80ms、停用快取；起點為導航，終點為正確車款首幀與車控就緒。原始逐幀數據在 [效能重驗目錄](evidence/carvue-recheck)，冷載資源與階段時間在 [首次回歸目錄](evidence/carvue-final)。各筆記錄包含實際 GLB SHA-256。

## 首次失敗與重驗

首次 248 案例包含 5 個測試判定問題，以及 94 個 Edge 沙箱啟動失敗。修正量測起點與鏡頭位移判定後，12 項相關 Chrome 檢查全部通過（另 10 項依解析度跳過）。Edge 改在可正常啟動的權限環境重跑，72 項通過、52 項依範圍跳過。產品執行程式與五份 GLB 在重驗前後沒有改變；原始失敗紀錄仍保留，不以重跑結果覆寫。逐案例合併結果見 [瀏覽器驗證摘要](evidence/browser-summary.json)。

78 個跳過項目包括只在 Chrome 1920×1080 執行的造型／效能與長測在其他環境的案例；不是未處理的功能失敗。正式產物驗證器另修正無副檔名 LICENSE 不一定有 Content-Type 的假設，仍逐檔檢查 HTTP 200 與內容雜湊。

首次長測在約 19 分 19 秒、234 次循環後，因本機開發伺服器拒絕連線而中斷，未達 30 分鐘，不能列為通過。已完成循環的幾何與貼圖數量均符合各車基準，沒有頁面例外。網路紀錄顯示預覽、manifest 與 favicon 同時發生 `ERR_CONNECTION_REFUSED`；尚無證據判定伺服器停止的根因。保留 [中斷紀錄](evidence/carvue-soak)，改用測試程序管理的專用伺服器重驗。

專用伺服器的 [完整長測](evidence/carvue-soak-managed/soak-30m.json) 實際執行 1,803,433ms（30 分 3 秒）、419 次五車輪替循環，幾何與貼圖數量每次均回到該車基準，持續繪製，頁面例外、主控台錯誤及模型下載失敗均為 0。這驗證指定工作負載下的資源數量與執行穩定性，不等於完整 JavaScript heap 或 GPU 記憶體分析。測試前後 [129 份檔案雜湊](evidence/release-snapshot.json) 一致，五份發布模型沒有變動。

## 乾淨副本與公開檔案

[乾淨副本紀錄](evidence/clean-clone.json) 對應獨立 Git clone，沒有沿用原專案 node_modules。安裝、87 項單元、型別與建置、素材／公開契約、實際 GLB 關節與開發伺服器入口均通過。副本實際儲存的 333 個 Git 物件全部屬於待發布分支，沒有其他本機快照物件。

`.gitattributes` 將文字正規化為 LF。原工作目錄與乾淨 checkout 的文字換行可能不同，因此文字原始雜湊與部分建置檔名可能不同；模型、可編輯來源與圖片按原始位元組比對。線上建置驗證從乾淨 checkout 執行，授權文字只正規化換行後比對。

## 靜態部署

執行 `npm run build`，`dist/` 包含網站、模型、預覽及授權文件。相對路徑搭配 Hash 路由支援專案子路徑，不需伺服器 rewrite；首版無 SEO 預渲染。使用 `npm run preview` 在本機預覽正式產物。

GitHub Actions 在推送 main 後執行型別、單元、素材契約及建置檢查，再部署 GitHub Pages。PR 只檢查，不部署；儲存庫的 Pages Source 設為 GitHub Actions。CI 不取代固定硬體上的效能與長測。

相依版本更新後執行 `node scripts/collect-notices.mjs` 更新第三方授權盤點。公開前的檔案與提交歷史檢查見 [隱私檢查](privacy-review.md)。

公開 [儲存庫](https://github.com/TsuNiWan/carvue) 與 [網站](https://tsuniwan.github.io/carvue/) 已建立。發布證據見 [CI 紀錄](evidence/publication.json)、[GitHub 乾淨副本](evidence/github-clone.json)、[線上五車驗證](evidence/published.json)、[README 圖片](evidence/github-readme.json)。公開副本的 356 個 Git 物件全部屬於 main 歷史，沒有額外本機快照物件；全部歷史 293 份 blob 掃描未發現已知憑證格式或私人目錄。
