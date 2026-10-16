# CARVUE 車映產品與交付追蹤

## 已確認範圍

桌機優先的 Vue／Three.js 互動賞車網站。保留五款既有造型，改用中性名稱與 ID；程式 MIT，車輛外觀另依 ASSET_RIGHTS.md 限定。無後端、會員與購車流程。使用者後續已授權建立 GitHub Pages，納入本次交付。

## 完成條件與狀態

狀態：待開始、進行中、待驗收、已完成、受阻。已完成必須附證據。

| 工作 | 負責面向 | 狀態 | 交付／驗證 |
| --- | --- | --- | --- |
| 網站更名與中性 ID | 前端／UX | 已完成 | src/data/vehicles.ts、中性資料契約及型別通過 |
| 模型徽標與中繼資料移除 | 3D 工程 | 已完成 | [來源稽核](evidence/source-audit.json)、[視覺審查](evidence/visual-review.json)、[素材契約](evidence/asset-validation.json) |
| 本機舊參考與歷史輸出清理 | 素材維護 | 已完成 | [清理摘要](evidence/cleanup-summary.json)，依使用者逐項清單授權 |
| 程式與素材授權範圍 | 發布審查 | 已完成 | [素材權利](../ASSET_RIGHTS.md)、[第三方聲明](../THIRD_PARTY_NOTICES.md) |
| 依賴授權盤點 | 工程 | 已完成 | [盤點](evidence/dependency-licenses.json)：111 個鎖定套件，86 個本機已安裝套件授權全文 |
| 新版功能／效能與長測 | QA | 已完成 | [驗證紀錄](verification.md)：170 項瀏覽器檢查通過、長測 30 分 3 秒／419 次循環 |
| README 實際截圖與文件 | UX／工程 | 已完成 | [README](../README.md)、[截圖紀錄](evidence/readme-capture.json) |
| 分拆提交、GitHub、乾淨 clone 與 CI | 發布工程 | 已完成 | [發布紀錄](evidence/publication.json)、[公開副本](evidence/github-clone.json)、[線上驗證](evidence/published.json) |
| 公開內容隱私檢查 | 發布審查 | 已完成 | [範圍與處理](privacy-review.md)、[公開歷史檢查](evidence/github-clone.json)，後續變更仍於推送前檢查 |

## 決策紀錄

- 公開名稱 CARVUE 車映；儲存庫優先 carvue，已存在則 carvue-showroom，不覆寫。
- 模型不是原創車型宣稱；去品牌與清除來源不代表取得外觀權利。
- 不保留舊車款路由別名；內容以版本化檔案維護。
- 車門全程 1.1 秒、後廂全程 1.4 秒，反向從當前姿態接續；減少動態下保留使用者主動觸發的機構展示時間。
- 提交按可審查的目的拆分；不提交工具、依賴、快取與大量歷史產物。

## 歷程摘要

早期原型依實車參考逐步建立比例、曲面、可見內裝、燈具及關節。後續完成載入競態處理、資源釋放、鍵盤與熱點操作、ADAS 通用情境及效能驗證。本版重新產生去品牌素材並以新雜湊重新驗證，舊版結果不視為新版通過證據。
