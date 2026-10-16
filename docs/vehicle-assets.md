# 展示模型維護

五款外觀源自既有實車參考重建，已移除品牌文字與識別幾何。外觀權利尚未確認，詳見 [素材權利](../ASSET_RIGHTS.md)。本文件不保留實車規配或車廠參考網址。

| ID | 名稱 | 建模入口 | 版本 |
| --- | --- | --- | --- |
| sedan-01 | 都會轎車 | build_sedan_01.py | 1.1.0 |
| suv-01 | 家庭休旅 | build_suv_01.py | 1.1.0 |
| sedan-02 | 流線轎車 | build_sedan_02.py | 1.1.0 |
| suv-02 | 都會休旅 | build_suv_02.py | 1.1.0 |
| sedan-03 | 行政轎車 | build_sedan_03.py | 1.1.0 |

來源在 assets/source/<id>/vehicle.blend；網站使用 public/models/<id>/1.1.0/vehicle.glb 與 manifest.json。預覽必須由同版模型產生。以 [驗證紀錄](verification.md) 記錄實際完成狀態，不以檔案存在代表造型通過。

## 建模規約

X 向左、Y 向上、Z 向前，單位公尺。車身底部落在共同地面；四門、後廂與兩個前輪使用獨立節點。Closed pose 儲存在 GLB 節點，manifest 描述旋轉軸、最大角度、燈組與熱點。不得在合併材質網格後才隱藏徽標；來源腳本不得產生品牌徽標。

## 重建

使用 Blender 4.5.14 LTS。工具不入庫，scripts/modeling/prepare-blender.mjs 可下載官方 Windows portable 並比對 SHA-256；解壓至 tools。執行方式見 README。每次改動先生成未壓縮 GLB，再使用 pack-model.mjs 無損壓縮；該腳本檢查頂點屬性、三角形方向、材質與節點一致。

四門與後廂的可見內部為展示用途的重建近似；細部結構不作實車精確性承諾。來源圖片與下載索引已清除，保留幾何程式與可編輯模型供後續修整。
