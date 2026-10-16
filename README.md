# CARVUE 車映

**轉個角度，探索車輛的每一面。**

[線上體驗](https://tsuniwan.github.io/carvue/#/vehicles) · [CI 與部署紀錄](https://github.com/TsuNiWan/carvue/actions/workflows/ci.yml)

以 Vue、TypeScript 與 Three.js 製作的桌機互動賞車網站，提供五款中性命名的 3D 展示模型、連續機構動畫與通用安全科技情境。

![五車總覽](docs/images/collection.webp)

## 互動體驗

- 拖曳旋轉、滾輪縮放，切換前、後、側面與俯視。
- 四門、後廂／尾門獨立開合，中途反向接續當前姿態。
- 頭尾燈漸亮、左右方向燈與雙黃燈、前輪 ±30° 轉向。
- 隨關節移動且判斷遮擋的熱點；面板保留等價操作。
- 三種安全科技通用情境，感測圖層及播放進度可調整。
- 按需載入、失敗重試、快速切車取消與 WebGL 資源釋放。

| 單車展示 | 開門與後廂 |
| --- | --- |
| ![單車展示](docs/images/showroom.webp) | ![四門與後廂開啟](docs/images/open-parts.webp) |

![安全科技示意](docs/images/safety.webp)

安全科技是通用原理示意，不代表實車配備。手機提供介紹與預覽；完整 3D 以桌機 Chrome／Edge 為驗收範圍。

## 本機啟動

需要 **Node.js 24 以上**與 npm。

```sh
npm ci
npm run dev
```

開啟 `http://127.0.0.1:5173/#/vehicles`。五款 ID 為 `sedan-01`、`suv-01`、`sedan-02`、`suv-02`、`sedan-03`；可直達 `#/vehicles/sedan-01`。

| 操作 | 方法 |
| --- | --- |
| 旋轉／縮放 | 拖曳／滾輪；聚焦畫布後使用方向鍵／加減鍵 |
| 重設視角 | 視角列或 Home |
| 車門與燈光 | 車上熱點或右側控制面板 |
| 重設控制 | 頂端「重設展示」，保留車款與模式 |
| 安全科技 | 右側切至「安全科技」 |

車門全程 1.1 秒、後廂 1.4 秒。減少動態偏好取消鏡頭飛行並縮短照明／轉向過渡；主動觸發的機構展示維持可觀察行程。

## 技術與目錄

Vue 3、Vue Router、TypeScript、Vite；Three.js 搭配 GLTFLoader、Meshopt 及 three-mesh-bvh。內容以版本化檔案維護，無後端或資料庫。

```text
src/views/            選車與展示頁面
src/components/       控制面板、熱點與 3D 畫面
src/three/            載入、關節適配與連續動畫
src/adas/             可獨立測試的安全科技情境
src/data/             車款清單與素材版本
public/models/        網站 GLB 與部件契約
assets/source/        可編輯 Blender 模型
scripts/modeling/     建模、匯出與壓縮
scripts/verification/ 正式產物與模型檢查
e2e/                  桌機互動、效能與長測
docs/                 設計、追蹤與驗證證據
```

## 驗證

```sh
npm run typecheck
npm test
npm run validate:assets
npm run validate:public
npm run test:rigs
npm run build
```

瀏覽器檢查需要 Chrome 與 Edge：

```sh
npm run test:e2e
npm run test:soak
node scripts/verification/verify-production.mjs carvue-production --final
```

四種環境為 Chrome／Edge × 1280×720／1920×1080。效能與 30 分鐘長測應在固定硬體單獨執行；CI 不取代 GPU 效能測試。實際結果見 [驗證紀錄](docs/verification.md)。

提交前執行 `node scripts/verification/staged-privacy.mjs` 掃描已暫存的變更，或加上 `--all` 掃描整個 Git index。它會檢查已知憑證格式、個人目錄與禁止入庫的檔案；圖片仍需人工檢視。不要提交 `.env`、本機設定、工具或原始測試 trace。

## 建模與內容維護

已附五款 `vehicle.blend`。重建使用 **Blender 4.5.14 LTS**，工具不入庫。Windows 可執行 `node scripts/modeling/prepare-blender.mjs` 下載並驗證官方壓縮檔，再解壓至 `tools/`。

以都會轎車為例（PowerShell 7）：

```powershell
& ./tools/blender-4.5.14-windows-x64/blender.exe --background --factory-startup --python-exit-code 1 --python scripts/modeling/build_sedan_01.py -- --export-only
Copy-Item public/models/sedan-01/1.1.0/vehicle.glb assets/source/sedan-01/vehicle.raw.glb
node scripts/modeling/pack-model.mjs assets/source/sedan-01/vehicle.raw.glb public/models/sedan-01/1.1.0/vehicle.glb
```

其餘入口見 [模型維護](docs/vehicle-assets.md)。改版同步更新清單、manifest、GLB、預覽與驗證紀錄。壓縮器比對精確頂點屬性、三角形方向、材質與節點；匯出成功不代表視覺驗收通過。

`scripts/modeling/audit-source.py` 檢查 Blender 圖片、外部連結與內嵌腳本並產生預覽 PNG；安裝 Python 的 Pillow 後執行 `scripts/verification/convert-images.py` 轉為 WebP。以 `node scripts/verification/capture-readme.mjs` 擷取網站，再執行轉檔腳本產生 README 圖片；不沿用舊圖。

## 建置與 GitHub Pages

```sh
npm run build
npm run preview
```

`dist/` 包含網站、模型、預覽及授權文件。相對路徑搭配 Hash 路由支援專案子路徑，不需伺服器 rewrite；首版無 SEO 預渲染。

GitHub Actions 在推送 main 後檢查、上傳產物並部署 GitHub Pages。PR 只檢查，不部署。Pages Source 設為 GitHub Actions。

## 授權與限制

程式與文字文件採 [MIT](LICENSE)。**車輛模型、可編輯幾何、預覽及截圖中的車輛外觀不在 MIT 授權範圍內**，詳見 [素材權利](ASSET_RIGHTS.md)。模型曾依實車參考重建，去品牌不表示原創車型，也不表示外觀權利已取得；本專案不提供全面不侵權保證。

第三方授權全文見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)，升級相依後執行 `node scripts/collect-notices.mjs` 更新盤點。必要通知隨網站產物交付。

[產品追蹤](docs/product-plan.md) · [UI／UX 規格](docs/design.md) · [模型維護](docs/vehicle-assets.md) · [驗證紀錄](docs/verification.md)
