# CIO 鎸佷箙鍖栧垵濮嬪寲璇存槑

## 1. 褰撳墠鎸佷箙鍖栬寖鍥?
涓烘妸 CIO 浠庘€滆繘绋嬪唴淇℃伅缂撳瓨鈥濆崌绾т负鈥滃彲杩芥函鐨勪俊鎭簳搴р€濓紝褰撳墠绯荤粺宸茬粡钀藉簱浜嗕笁绫绘牳蹇冩暟鎹細

- `artifact_records`
- `information_events`
- `knowledge_assets`

瀵瑰簲妯″瀷鏂囦欢锛?
- `src/app/models/artifact.py`
- `src/app/models/information_event.py`
- `src/app/models/knowledge_asset.py`

姝ゅ锛屼笌娌荤悊鐩稿叧鐨?`leader_reports` 涔熷凡缁忔寔涔呭寲锛屼絾瀹冨睘浜?CEO 鎶ュ憡涓績锛屼笉灞炰簬 CIO 鏍稿績浠撳簱琛ㄦ湰韬€?
## 2. 鍒濆鍖栬矾寰?
褰撳墠椤圭洰杩樻病鏈夌嫭绔嬭縼绉绘鏋讹紝浠嶉噰鐢ㄨ交閲忓垵濮嬪寲鏂瑰紡锛?
- `src/main.py`
- `src/app/db/session.py`

鍚姩杩囩▼濡備笅锛?
1. FastAPI 搴旂敤鍚姩
2. 瑙﹀彂 `startup_event`
3. 璋冪敤 `init_db()`
4. `init_db()` 閫氳繃 `Base.metadata.create_all()` 鍒涘缓缂哄け琛?
杩欐剰鍛崇潃锛?
- 鏂扮幆澧冮娆″惎鍔ㄦ椂锛屼細鑷姩琛ラ綈 CIO 鐩稿叧琛?- 娴嬭瘯鐜涓殑鏁版嵁搴撲篃浼氳嚜鍔ㄥ垵濮嬪寲

## 3. 褰撳墠瀹炵幇鏄惁鍑嗙‘

鏍规嵁鐜版湁浠ｇ爜锛岃繖浠借鏄庡湪澶ф柟鍚戜笂鏄噯纭殑锛屼絾闇€瑕佽ˉ鍏呬袱鐐癸細

1. CIO 宸蹭笉鏄函鍐呭瓨浠撳簱锛屾枃妗ｅ繀椤绘槑纭繖涓€鐐广€?2. 褰撳墠闄や簡 CIO 涓夊紶鏍稿績琛ㄥ锛屾不鐞嗗眰杩樻柊澧炰簡 `leader_reports`锛屽畠涓?CEO 鎶ュ憡鏈哄埗鐩稿叧锛屽垵濮嬪寲璺緞鐩稿悓銆?
## 4. 榛樿鐭ヨ瘑璧勪骇

`knowledge_assets` 閲囩敤鎳掑垵濮嬪寲鏂瑰紡銆?
棣栨璁块棶 CIO 鐭ヨ瘑搴撴椂锛屽鏋滄暟鎹簱涓琛ㄤ负绌猴紝浼氳嚜鍔ㄥ啓鍏ラ粯璁よ祫浜э紝涓昏鍖呮嫭锛?
- 鐖嗘妗堜緥
- 妯℃澘
- 骞冲彴鎶曟斁鎸囧崡

榛樿鏁版嵁瀹氫箟浣嶇疆锛?
- `src/app/services/cio.py`

## 5. 浣跨敤涓殑闄愬埗

褰撳墠 `create_all()` 鏂规閫傚悎蹇€熸帹杩涳紝浣嗘湁鏄庢樉杈圭晫锛?
1. 瀹冨彧鑳藉垱寤轰笉瀛樺湪鐨勮〃
2. 瀹冧笉浼氳嚜鍔ㄤ慨鏀瑰凡鏈夎〃缁撴瀯
3. 濡傛灉鍚庣画瀛楁鍙樺寲棰戠箒锛屼粎闈?`create_all()` 浼氳秺鏉ヨ秺闅剧淮鎶?
鎵€浠ュ畠閫傚悎浣滀负褰撳墠闃舵鐨勫惎鍔ㄦ柟妗堬紝浣嗕笉閫傚悎浣滀负闀挎湡杩佺Щ鏂规銆?
## 6. 寤鸿楠岃瘉鏂瑰紡

鍦ㄥ紑鍙戠幆澧冧腑锛屽彲浠ユ墜鍔ㄦ墽琛屼竴娆℃樉寮忓垵濮嬪寲妫€鏌ワ細

```powershell
cd E:\2026OPC澶ц禌\榫欒櫨娴佺▼\src
.\.venv\Scripts\python.exe -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"
```

闅忓悗鍙鏌ワ細

- `/api/v1/ceo/company-status`
- `/api/v1/cmo/chat`
- `/api/v1/workflows/runs`

濡傛灉杩欎簺鎺ュ彛姝ｅ父杩斿洖锛岄€氬父璇存槑鏁版嵁搴撳垵濮嬪寲閾捐矾鏄彲鐢ㄧ殑銆?
## 7. 涓嬩竴姝ュ缓璁?
涓嬩竴闃舵鏈€鍊煎緱琛ョ殑鏄寮忚縼绉讳綋绯伙細

1. 寮曞叆 Alembic
2. 涓?`artifact_records`銆乣information_events`銆乣knowledge_assets`銆乣leader_reports` 寤虹珛杩佺Щ鑴氭湰
3. 鍚庣画琛ㄧ粨鏋勫彉鏇村叏閮ㄨ蛋 migration锛岃€屼笉鍐嶄緷璧?`create_all()`

