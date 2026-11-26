# 分镜头剧本：《雍正王朝第12集改编：白宫乾清宫议举新CEO与黄仁勋复立风云》（终审31镜完整版 · 三参考图多角度 Ref2VA 直出 · 全中文配音）

- **项目 ID**：`02_yongzheng_ep12_huang`
- **原始剧本来源**：[`source_script.md`](./source_script.md)（终审台本 100% 逐句完整拆解，零删节、零截断）
- **原剧参考源**：《雍正王朝》第 12 集「康熙召集满朝文武议举新太子」（`https://www.youtube.com/watch?v=ptQeyZ7y73I`）
- **生成引擎与直出模式**：MiniMax H3 33.1B 未剪枝 BF16（`minimax_h3_ref2va_bf16` + `Turbo LoRA`），全片 31 镜统一采用 **`minimax_h3_ref2va_multi3_api.json`（主角双视角单人肖像 `<Picture 1>` + `<Picture 2>` + 对手/群臣 `<Picture 3>` 原生三图直出，彻底消除拼图分屏伪影）**
- **全片规模与 H3 15 秒红线**：共 **`31` 镜**，总时长 **`401.00 秒`**（约 `6 分 41.0 秒`）；单镜严格 `≤ 14.38s`（`17k + 5` 时间网格 @ `24 fps`），中文台词容量按 `3.0~3.5 字/秒` 精确核算
- **中文配音与本尊音色锁死**：原生 **32kHz 双声道立体声中文配音（Mandarin Chinese）**，每镜画面动作段与末尾 `Audio:` 段中文引号台词 100% 一字不差，并显式绑定各人物本尊真实声纹特征；Negative Prompt 强制加入 `English speech` 抑制英文发音

---

## 一、终审七方角色替换与多角度参考图总表（`characters/`）

| 人物 ID (`character_id`) | 原片角色 | 替换目标人物 | 双视角单人肖像 (`<Picture 1>` / `<Picture 2>`) | 中文配音本尊音色特征 (`voice_anchor_en`) |
| :--- | :--- | :--- | :--- | :--- |
| `trump` | **康熙皇帝** | **特朗普 (Donald Trump)** | `ref_trump_front.png` + `ref_trump_half.png` | 低沉沙哑、顿挫有力、极具统治力的特朗普本尊男中音讲中文 |
| `jensen_huang` | **太子 / 二阿哥胤礽** | **黄仁勋 (Jensen Huang · CEO)** | `ref_jensen_huang_front.png` + `ref_jensen_huang_half.png` | 温和磁性、略带台湾国语亲切腔调的黄仁勋本尊男声讲中文 |
| `scott_bessent` | **张廷玉** | **贝森特 (Scott Bessent)** | `ref_scott_bessent_front.png` + `ref_scott_bessent_half.png` | 沉稳儒雅、咬字清晰的华尔街财长深沉男中音讲中文 |
| `marco_rubio` | **佟国维** | **鲁比奥 (Marco Rubio)** | `ref_marco_rubio_front.png` + `ref_marco_rubio_half.png` | 语速明快、清亮急促、极具攻击性的辩论派男声讲中文 |
| `jd_vance` | **马齐（马奇）** | **万斯 (JD Vance)** | `ref_jd_vance_front.png` + `ref_jd_vance_half.png` | 浑厚低沉、谨慎中透着精明算计的男中音讲中文 |
| `democrats` | **其余朝臣（左列）** | **民主党人士换脸群像** | `characters/democrats/ref_democrats.png`（4人参考） | 匹配舒默、佩洛西、沃伦、杰弗里斯面孔换脸 |
| `republicans` | **其余朝臣（右列）** | **共和党人士换脸群像** | `characters/republicans/ref_republicans.png`（4人参考） | 匹配约翰逊、卢特尼克、麦康奈尔、图恩面孔换脸 |

---

## 二、31 镜完整「三参考图多角度 Ref2VA 直出」分镜节拍总表

| 镜号 (`task_id`) | 所属场次 | 成片累计起点 | 戏剧节拍 (L2/L3) | `<Picture 1>`+`<Picture 2>` (主角双视角) | `<Picture 3>` (对手/群臣) | 帧数 (`17k+5`) | 时长 (`≤15s`) | 终审中文配音台词 |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :---: | :--- |
| `yz12_huang_shot01` | `scene01_qianqing_palace` | `0.00s` | 起（开场宣旨）· 特朗普端坐御案宣布议举新CEO | `特朗普（替康熙）` (双视角) | `共和党人士换脸群臣` | `243` (`k=14`) | **10.12s** | 【特朗普】「朕今天和你们一道议举新CEO。记得是在十一月十二日，朕在上谕中说过，」 |
| `yz12_huang_shot02` | `scene01_qianqing_palace` | `10.12s` | 起（重申上谕）· 明确白宫内阁与英伟达董事会皆可推举 | `特朗普（替康熙）` (双视角) | `民主党人士换脸群臣` | `345` (`k=20`) | **14.38s** | 【特朗普】「白宫内阁、英伟达董事会，都可以推举一位人选作为新CEO的人选。朕一惟公议是从，决无偏私。」 |
| `yz12_huang_shot03` | `scene02_imperial_desk_memorial` | `24.50s` | 承（质疑荐章）· 翻看御案满桌联名荐章提出质疑 | `特朗普（替康熙）` (双视角) | `共和党人士换脸群臣` | `345` (`k=20`) | **14.38s** | 【特朗普】「现在这荐章都上来了，从这些荐章的情况来看，新CEO的人选似乎已经出来了。可是这些荐章又能说明什么？」 |
| `yz12_huang_shot04` | `scene01_qianqing_palace` | `38.88s` | 承（直刺人心）· 质问白宫内阁推举的人是否自己看准 | `特朗普（替康熙）` (双视角) | `民主党人士换脸群臣` | `345` (`k=20`) | **14.38s** | 【特朗普】「英伟达董事会的不说，白宫内阁的你们都来了，你们推举的人都是你们自己看准的吗？我看未必见得。」 |
| `yz12_huang_shot05` | `scene01_qianqing_palace` | `53.25s` | 转（御前点名）· 点名鲁比奥与万斯出列并质问黄仁勋荐章 | `特朗普（替康熙）` (双视角) | `万斯（替马齐）` | `192` (`k=11`) | **8.00s** | 【特朗普】「鲁比奥、万斯！」 / 【万斯】「臣在。」 / 【特朗普】「为什么没有黄仁勋的荐章？」 |
| `yz12_huang_shot06` | `scene01_qianqing_palace` | `61.25s` | 承（鲁比奥装糊涂）· 鲁比奥单人回话反问何来推举黄仁勋荐章 | `鲁比奥（替佟国维）` (双视角) | `特朗普（替康熙）` | `294` (`k=17`) | **12.25s** | 【鲁比奥】「总统这话奴才不明白，因为废黄仁勋，所以才推荐新CEO，怎么还会有推举黄仁勋的荐章？」 |
| `yz12_huang_shot07` | `scene02_imperial_desk_memorial` | `73.50s` | 转（层层紧逼）· 特朗普戳破狡辩追问有没有人推举黄仁勋 | `特朗普（替康熙）` (双视角) | `鲁比奥（替佟国维）` | `294` (`k=17`) | **12.25s** | 【特朗普】「朕现在不是问你应不应该推举黄仁勋，而是问你有没有人推举黄仁勋！」 |
| `yz12_huang_shot08` | `scene01_qianqing_palace` | `85.75s` | 承（排除老黄旧部）· 鲁比奥点名科莱特、马拉科夫斯基与杰伊·普里 | `鲁比奥（替佟国维）` (双视角) | `民主党人士换脸群臣` | `345` (`k=20`) | **14.38s** | 【鲁比奥】「有倒是有，不过多数是前CEO一党的人，像科莱特·克雷斯、马拉科夫斯基、杰伊·普里等，他们写的荐章当然不能作数。」 |
| `yz12_huang_shot09` | `scene01_qianqing_palace` | `100.12s` | 转（突问马斯克）· 特朗普冷冷追问马斯克，鲁比奥秒拒 | `特朗普（替康熙）` (双视角) | `鲁比奥（替佟国维）` | `192` (`k=11`) | **8.00s** | 【特朗普】「那么马斯克呢？」 / 【鲁比奥】「马斯克的荐章也不能作数。」 |
| `yz12_huang_shot10` | `scene01_qianqing_palace` | `108.12s` | 承（搬出白宫犯上）· 鲁比奥称马斯克十一月十二日在白宫椭圆形办公室狂悖犯上 | `鲁比奥（替佟国维）` (双视角) | `特朗普（替康熙）` | `345` (`k=20`) | **14.38s** | 【鲁比奥】「马斯克十一月十二日在白宫椭圆形办公室狂悖犯上，当时就被总统驳斥了，所以他写的荐章也不能作数。」 |
| `yz12_huang_shot11` | `scene01_qianqing_palace` | `122.50s` | 转（全场破冰）· 特朗普扫视群臣，贝森特（替张廷玉）独自出列保举黄仁勋 | `特朗普（替康熙）` (双视角) | `贝森特（替张廷玉）` | `294` (`k=17`) | **12.25s** | 【特朗普】「你们、你们……你们中间，有没有人推举黄仁勋的？」 / 【贝森特】「有，臣推举的就是黄仁勋。」 |
| `yz12_huang_shot12` | `scene02_imperial_desk_memorial` | `134.75s` | 承（御前剖白）· 特朗普主动回应外界对“出尔反尔”的猜疑 | `特朗普（替康熙）` (双视角) | `贝森特（替张廷玉）` | `294` (`k=17`) | **12.25s** | 【特朗普】「你们有些事可能会觉得很奇怪，甚至有人会认为朕是出尔反尔。这里，朕要说明一下：」 |
| `yz12_huang_shot13` | `scene02_imperial_desk_memorial` | `147.00s` | 承（厘清责任）· 点明废黜CEO系英伟达董事会独断专行，自己当时驻跸海湖庄园 | `特朗普（替康熙）` (双视角) | `共和党人士换脸群臣` | `345` (`k=20`) | **14.38s** | 【特朗普】「废黜CEO，是英伟达董事会独断专行，事先没有和你们商量。这有几个原因：一是朕当时驻跸海湖庄园，」 |
| `yz12_huang_shot14` | `scene02_imperial_desk_memorial` | `161.38s` | 承（国运大局）· 阐明当时情形晦暗，为美股AI霸权与美利坚国运先稳大局 | `特朗普（替康熙）` (双视角) | `民主党人士换脸群臣` | `345` (`k=20`) | **14.38s** | 【特朗普】「事起肘腋之间，许多情形晦暗不明，为美股与AI霸权想、为美利坚国运想，也不得不先稳大局；」 |
| `yz12_huang_shot15` | `scene02_imperial_desk_memorial` | `175.75s` | 承（回溯风波）· 提及黄仁勋当时风波虽难解，但事后看来大有隐情 | `特朗普（替康熙）` (双视角) | `黄仁勋（替太子/CEO）` | `345` (`k=20`) | **14.38s** | 【特朗普】「二是当时黄仁勋的荒诞不经，实在是叫人不可忍，也不可解。但事后看来，他的那些事情，」 |
| `yz12_huang_shot16` | `scene02_imperial_desk_memorial` | `190.12s` | 转（亮出奇折）· 定性黄仁勋遭暗算，举起贝森特奏折赞其写得好 | `特朗普（替康熙）` (双视角) | `贝森特（替张廷玉）` | `345` (`k=20`) | **14.38s** | 【特朗普】「有些是捕风捉影、纯属子虚，有的则是著了别人的暗算，才使得一时失察、进退失据。贝森特的折子写得好：」 |
| `yz12_huang_shot17` | `scene02_imperial_desk_memorial` | `204.50s` | 转（高光名句）· 宣读“无心为恶虽恶不罚、退居外部正合外部寻帅之规” | `特朗普（替康熙）` (双视角) | `黄仁勋（替太子/CEO）` | `345` (`k=20`) | **14.38s** | 【特朗普】「所谓无心为恶，虽恶不罚。况且黄仁勋之过因风波所致，如今既已辞职退居外部，正合外部寻帅之规。」 |
| `yz12_huang_shot18` | `scene02_imperial_desk_memorial` | `218.88s` | 承（制度善后）· 宣读“外设首席合规官治其弊，内礼聘归位感其心” | `特朗普（替康熙）` (双视角) | `贝森特（替张廷玉）` | `345` (`k=20`) | **14.38s** | 【特朗普】「伏祈总统念昔日知遇之情、施宽容之道，外则增设首席合规官以制度治其弊，内则礼聘归位以圣意感其心，」 |
| `yz12_huang_shot19` | `scene02_imperial_desk_memorial` | `233.25s` | 合（奏折落款点名）· 宣读结尾并高呼“贝森特！”，贝森特恭敬应“臣在！” | `特朗普（替康熙）` (双视角) | `贝森特（替张廷玉）` | `345` (`k=20`) | **14.38s** | 【特朗普】「倘能使黄仁勋重振英伟达、修心向善，则不仅为硅谷之福，亦美利坚与天下股民之福。——贝森特！」 / 【贝森特】「臣在！」 |
| `yz12_huang_shot20` | `scene02_imperial_desk_memorial` | `247.62s` | 承（嘉奖贝森特）· 盛赞贝森特书读得好、以美利坚AI江山社稷为重 | `特朗普（替康熙）` (双视角) | `贝森特（替张廷玉）` | `345` (`k=20`) | **14.38s** | 【特朗普】「你这个书读得好！好就好在，时刻不忘大局的忠恕之道，与人为善；好就好在时刻以美利坚AI江山社稷为重，」 |
| `yz12_huang_shot21` | `scene02_imperial_desk_memorial` | `262.00s` | 转（话锋骤寒）· 痛斥趋红踩黑、只顾选票与禄位的政客 | `特朗普（替康熙）` (双视角) | `鲁比奥（替佟国维）` | `294` (`k=17`) | **12.25s** | 【特朗普】「而不像有些人，趋红踩黑、见风使舵，想的不是江山社稷，而是他自己的选票与禄位！」 |
| `yz12_huang_shot22` | `scene01_qianqing_palace` | `274.25s` | 起（正面发难）· 质问鲁比奥两百多名两党议员联名折子是如何串联的 | `特朗普（替康熙）` (双视角) | `鲁比奥（替佟国维）` | `345` (`k=20`) | **14.38s** | 【特朗普】「鲁比奥，这两百多名两党议员联名的折子，是怎么回事？如果没有人居中联络，这么多人就同声一气、众口一词？」 |
| `yz12_huang_shot23` | `scene01_qianqing_palace` | `288.62s` | 承（鲁比奥硬顶）· 辩称居中联络是白宫内阁责任，推举雷内·哈斯乃公意 | `鲁比奥（替佟国维）` (双视角) | `民主党人士换脸群臣` | `345` (`k=20`) | **14.38s** | 【鲁比奥】「回总统，居中联络本就是白宫内阁的责任，推举Arm的雷内·哈斯也是白宫内阁和许多两党官员的公意，」 |
| `yz12_huang_shot24` | `scene01_qianqing_palace` | `303.00s` | 转（针锋相对）· 鲁比奥自称无可指责，特朗普大笑讽刺其独代表白宫内阁 | `鲁比奥（替佟国维）` (双视角) | `特朗普（替康熙）` | `345` (`k=20`) | **14.38s** | 【鲁比奥】「这些都是为了我美利坚的AI江山社稷，奴才以为无可指责！」 / 【特朗普】「白宫内阁，哈哈……你一个人代表白宫内阁？」 |
| `yz12_huang_shot25` | `scene01_qianqing_palace` | `317.38s` | 承（当庭对质）· 特朗普转问同为内阁大臣的贝森特 | `特朗普（替康熙）` (双视角) | `贝森特（替张廷玉）` | `243` (`k=14`) | **10.12s** | 【特朗普】「贝森特，你也是白宫内阁大臣，你说说鲁比奥有没有居中联络？」 |
| `yz12_huang_shot26` | `scene01_qianqing_palace` | `327.50s` | 承（贝森特圆场）· 贝森特老练滴水不漏，先肯定雷内·哈斯并替同僚留余地 | `贝森特（替张廷玉）` (双视角) | `鲁比奥（替佟国维）` | `345` (`k=20`) | **14.38s** | 【贝森特】「回总统，鲁比奥和万斯保举雷内·哈斯，那是因为雷内·哈斯确实有过人之处，臣以为这无可厚非；」 |
| `yz12_huang_shot27` | `scene01_qianqing_palace` | `341.88s` | 转（绵里藏针）· 贝森特点出串联系“一时不慎忘了君子不党之训” | `贝森特（替张廷玉）` (双视角) | `万斯（替马齐）` | `243` (`k=14`) | **10.12s** | 【贝森特】「至于众人串联之事，那也是因为一时不慎忘了君子不党的教训。」 |
| `yz12_huang_shot28` | `scene01_qianqing_palace` | `352.00s` | 转（图穷匕见）· 鲁比奥公开逼问为何国会两党与白宫众臣不能保举雷内·哈斯 | `鲁比奥（替佟国维）` (双视角) | `特朗普（替康熙）` | `345` (`k=20`) | **14.38s** | 【鲁比奥】「奴才岂敢，只是……只是奴才斗胆问一句，为什么国会两党与白宫众臣不能够保举雷内·哈斯？请总统明示！」 |
| `yz12_huang_shot29` | `scene01_qianqing_palace` | `366.38s` | 转（老底威慑 & 万斯硬顶）· 特朗普寒声警告，万斯（替马齐）硬着头皮出列附议 | `特朗普（替康熙）` (双视角) | `万斯（替马齐）` | `345` (`k=20`) | **14.38s** | 【特朗普】「你真要朕把你的老底都掀出来吗？」 / 【万斯】「总统，臣也以为，诸候选人之中，唯雷内·哈斯宜乎立为新CEO……」 |
| `yz12_huang_shot30` | `scene01_qianqing_palace` | `380.75s` | 高潮（雷霆震怒）· 特朗普拍案怒斥万斯“朕看你才是真糊涂！” | `特朗普（替康熙）` (双视角) | `万斯（替马齐）` | `192` (`k=11`) | **8.00s** | 【特朗普】「刚才卢特尼克说鲁比奥糊涂，朕看你才是真糊涂！」 |
| `yz12_huang_shot31` | `scene01_qianqing_palace` | `388.75s` | 合（定鼎收官）· 降万斯两级列贝森特之后，黄仁勋复立大局已定 | `特朗普（替康熙）` (双视角) | `黄仁勋（替太子/CEO）` | `294` (`k=17`) | **12.25s** | 【特朗普】「你的罪在于见事昏愦，随声附和！朕降你两级，仍在白宫内阁行走，列在贝森特之后！」 |

---

## 三、L4 逐镜导演台本与镜头内微时间轴（全部 31 镜）

### 分镜 01（`yz12_huang_shot01`）· 起（开场宣旨）· 特朗普端坐御案宣布议举新CEO
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`243 帧` / `24 fps` = **`10.12 秒`**（`k=14`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2101`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/republicans/ref_republicans.png`（共和党人士换脸群臣）
- **中文台词与本尊音色对齐**：【特朗普】「朕今天和你们一道议举新CEO。记得是在十一月十二日，朕在上谕中说过，」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：沿用 乾清宫全景开场，御案上的康熙替换为 `<Picture 1>`+`<Picture 2>` 特朗普，满朝文武换脸为民主党与共和党人士；
  - [2.6s - 10.13s]：特朗普目光威严扫视全殿，用标志性沙哑男中音开口讲中文台词。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Republican Party court officials (Mike Johnson, Howard Lutnick, Mitch McConnell, John Thune)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium-wide establishing imperial court shot inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.6s] Behind the imperial dragon desk sits the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads, gazing authoritatively across the hall packed with recognizable Republican Party politicians (resembling Mike Johnson, Mitch McConnell, and Howard Lutnick) face-swapped onto Qing court officials in crimson-trimmed official robes and Democratic face-swapped ministers. [2.6s-10.13s] Leaning forward with steady commanding presence, the Emperor speaks in Mandarin Chinese: '朕今天和你们一道议举新CEO。记得是在十一月十二日，朕在上谕中说过，' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, solemn imperial gong echo fading into deep palace silence, subtle orchestral bass undertone, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '朕今天和你们一道议举新CEO。记得是在十一月十二日，朕在上谕中说过，'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 02（`yz12_huang_shot02`）· 起（重申上谕）· 明确白宫内阁与英伟达董事会皆可推举
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2102`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/democrats/ref_democrats.png`（民主党人士换脸群臣）
- **中文台词与本尊音色对齐**：【特朗普】「白宫内阁、英伟达董事会，都可以推举一位人选作为新CEO的人选。朕一惟公议是从，决无偏私。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 3.0s]：镜头随 缓推至御案，特朗普抬起标志性手势重申公推范围；
  - [3.0s - 10.0s]：点出“白宫内阁、英伟达董事会，都可以推举一位人选作为新CEO的人选”；
  - [10.0s - 14.38s]：沉声强调“朕一惟公议是从，决无偏私”，殿下两党百官屏息凝神。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Democratic Party court ministers (Chuck Schumer, Nancy Pelosi, Elizabeth Warren, Hakeem Jeffries)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Slow steady push-in medium shot on the throne dais inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-3.0s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads raises his signature expressive hand over the yellow memorials while recognizable Democratic Party politicians (resembling Chuck Schumer, Nancy Pelosi, and Elizabeth Warren) face-swapped onto Qing court ministers in dark royal-blue official robes and Republican ministers listen tensely below. [3.0s-14.38s] Looking intently across the court, the Emperor speaks in Mandarin Chinese: '白宫内阁、英伟达董事会，都可以推举一位人选作为新CEO的人选。朕一惟公议是从，决无偏私。' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, crisp tap of fingers on the wooden imperial desk, hushed intake of breath across the hall, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '白宫内阁、英伟达董事会，都可以推举一位人选作为新CEO的人选。朕一惟公议是从，决无偏私。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 03（`yz12_huang_shot03`）· 承（质疑荐章）· 翻看御案满桌联名荐章提出质疑
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2103`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/republicans/ref_republicans.png`（共和党人士换脸群臣）
- **中文台词与本尊音色对齐**：【特朗普】「现在这荐章都上来了，从这些荐章的情况来看，新CEO的人选似乎已经出来了。可是这些荐章又能说明什么？」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 3.2s]：特朗普低头轻拂御案上堆叠如山的明黄荐章，神色由平静转为锐利；
  - [3.2s - 14.38s]：抬眼冷峻质问满朝百官这些荐章究竟能说明什么，营造强烈压迫感。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Republican Party court officials (Mike Johnson, Howard Lutnick, Mitch McConnell, John Thune)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up shot over the stack of yellow silk memorials inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-3.2s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads runs his hand across the towering stack of yellow silk recommendation memorials while recognizable Republican Party politicians (resembling Mike Johnson, Mitch McConnell, and Howard Lutnick) face-swapped onto Qing court officials in crimson-trimmed official robes exchange uneasy glances below. [3.2s-14.38s] Lifting his sharp gaze with skepticism, the Emperor speaks in Mandarin Chinese: '现在这荐章都上来了，从这些荐章的情况来看，新CEO的人选似乎已经出来了。可是这些荐章又能说明什么？' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, crisp paper rustling as yellow silk memorials shift on the desk, low brooding strings, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '现在这荐章都上来了，从这些荐章的情况来看，新CEO的人选似乎已经出来了。可是这些荐章又能说明什么？'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 04（`yz12_huang_shot04`）· 承（直刺人心）· 质问白宫内阁推举的人是否自己看准
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2104`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/democrats/ref_democrats.png`（民主党人士换脸群臣）
- **中文台词与本尊音色对齐**：【特朗普】「英伟达董事会的不说，白宫内阁的你们都来了，你们推举的人都是你们自己看准的吗？我看未必见得。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 3.0s]：镜头随 扫过殿下鸦雀无声的民主党与共和党换脸群臣；
  - [3.0s - 14.38s]：特朗普冷笑发问，直指“我看未必见得”，殿内气压骤降。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Democratic Party court ministers (Chuck Schumer, Nancy Pelosi, Elizabeth Warren, Hakeem Jeffries)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Sweeping medium court shot following the Emperor's gaze inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-3.0s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads narrows his eyes as his gaze sweeps over recognizable Democratic Party politicians (resembling Chuck Schumer, Nancy Pelosi, and Elizabeth Warren) face-swapped onto Qing court ministers in dark royal-blue official robes and Republican ministers standing rigidly on the stone floor. [3.0s-14.38s] With cold incisive sarcasm, the Emperor speaks in Mandarin Chinese: '英伟达董事会的不说，白宫内阁的你们都来了，你们推举的人都是你们自己看准的吗？我看未必见得。' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, subtle creak of timber hall pillars, taut cello suspense drone, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '英伟达董事会的不说，白宫内阁的你们都来了，你们推举的人都是你们自己看准的吗？我看未必见得。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 05（`yz12_huang_shot05`）· 转（御前点名）· 点名鲁比奥与万斯出列并质问黄仁勋荐章
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`192 帧` / `24 fps` = **`8.00 秒`**（`k=11`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2105`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/jd_vance/ref_jd_vance_front.png`（万斯（替马齐））
- **中文台词与本尊音色对齐**：【特朗普】「鲁比奥、万斯！」 / 【万斯】「臣在。」 / 【特朗普】「为什么没有黄仁勋的荐章？」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.2s]：特朗普沉声喝点“鲁比奥、万斯！”；
  - [2.2s - 4.2s]：鲁比奥与 `<Picture 3>` 万斯齐步出列躬身应答“臣在。”；
  - [4.2s - 8.00s]：特朗普直截了当抛出一记灵魂发问：“为什么没有黄仁勋的荐章？”
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (JD Vance portraying Grand Secretary Maci) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Shot-reverse-shot medium framing between throne and cabinet ministers inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.2s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads calls out sharply in Mandarin Chinese: '鲁比奥、万斯！' [2.2s-4.2s] Beside Marco Rubio, the 42-year-old bearded Grand Secretary looking like JD Vance with a neatly trimmed full dark beard and piercing blue eyes wearing a first-rank Qing Dynasty official court robe and red-tasseled court hat steps forward immediately and bows in unison, answering in Mandarin Chinese: '臣在。' [4.2s-8.0s] The Emperor immediately presses them in Mandarin Chinese: '为什么没有黄仁勋的荐章？' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, brisk footsteps of two ministers stepping onto stone floor, rustle of heavy silk court robes, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '鲁比奥、万斯！', speaking in Mandarin Chinese with JD Vance's exact vocal timbre, grounded resonant mid-low baritone voice and cautious calculated political cadence: '臣在。', speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '为什么没有黄仁勋的荐章？'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 06（`yz12_huang_shot06`）· 承（鲁比奥装糊涂）· 鲁比奥单人回话反问何来推举黄仁勋荐章
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`294 帧` / `24 fps` = **`12.25 秒`**（`k=17`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2106`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/marco_rubio/ref_marco_rubio_half.png`（鲁比奥（替佟国维） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙））
- **中文台词与本尊音色对齐**：【鲁比奥】「总统这话奴才不明白，因为废黄仁勋，所以才推荐新CEO，怎么还会有推举黄仁勋的荐章？」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：还原原剧佟国维单人应对机位，替换为 `<Picture 1>`+`<Picture 2>` 鲁比奥躬身拱手故作不解；
  - [2.6s - 12.25s]：鲁比奥以清亮急促的辩论男声回话，试图用“既废黄仁勋何来荐章”搪塞过去。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Marco Rubio portraying Grand Secretary Tong Guowei), and use <Picture 3> as facial identity reference for the secondary character (Donald Trump portraying the Qing Emperor) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up on Grand Secretary Tong Guowei's blocking inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.6s] the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads bows politely yet guardedly before the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads, while Democratic and Republican face-swapped officials watch intently from behind. [2.6s-12.25s] Raising his eyes with calculated innocence, Marco Rubio replies alone in Mandarin Chinese: '总统这话奴才不明白，因为废黄仁勋，所以才推荐新CEO，怎么还会有推举黄仁勋的荐章？' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, subtle cloth rustle of raised sleeves, quiet resonant hall acoustics, speaking in Mandarin Chinese with Marco Rubio's exact vocal timbre, sharp rapid high-energy clear tenor-baritone voice and assertive confrontational political debater cadence: '总统这话奴才不明白，因为废黄仁勋，所以才推荐新CEO，怎么还会有推举黄仁勋的荐章？'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 07（`yz12_huang_shot07`）· 转（层层紧逼）· 特朗普戳破狡辩追问有没有人推举黄仁勋
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`294 帧` / `24 fps` = **`12.25 秒`**（`k=17`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2107`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维））
- **中文台词与本尊音色对齐**：【特朗普】「朕现在不是问你应不应该推举黄仁勋，而是问你有没有人推举黄仁勋！」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.5s]：特朗普神色骤冷，打断 `<Picture 3>` 鲁比奥的太极推手；
  - [2.5s - 12.25s]：手指直指殿下，一字一顿逼问“有没有人推举黄仁勋！”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Marco Rubio portraying Grand Secretary Tong Guowei) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Tight medium close-up on the Emperor pushing forward inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.5s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads leans intently over the dragon desk, cutting off the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads with an unyielding glare. [2.5s-12.25s] Pointing emphatically downward, the Emperor presses in Mandarin Chinese: '朕现在不是问你应不应该推举黄仁勋，而是问你有没有人推举黄仁勋！' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, sharp wooden desk knock, rising low-frequency suspense pulse, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '朕现在不是问你应不应该推举黄仁勋，而是问你有没有人推举黄仁勋！'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 08（`yz12_huang_shot08`）· 承（排除老黄旧部）· 鲁比奥点名科莱特、马拉科夫斯基与杰伊·普里
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2108`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/marco_rubio/ref_marco_rubio_half.png`（鲁比奥（替佟国维） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/democrats/ref_democrats.png`（民主党人士换脸群臣）
- **中文台词与本尊音色对齐**：【鲁比奥】「有倒是有，不过多数是前CEO一党的人，像科莱特·克雷斯、马拉科夫斯基、杰伊·普里等，他们写的荐章当然不能作数。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.4s]：`<Picture 1>`+`<Picture 2>` 鲁比奥神情微滞，随即镇定应对，身后两党换脸百官暗自侧耳；
  - [2.4s - 14.38s]：鲁比奥流畅念出英伟达内部力挺黄仁勋的科莱特·克雷斯、马拉科夫斯基、杰伊·普里，称其荐章不能作数（严格去除原句冗余）。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Marco Rubio portraying Grand Secretary Tong Guowei), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Democratic Party court ministers (Chuck Schumer, Nancy Pelosi, Elizabeth Warren, Hakeem Jeffries)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up on Tong Guowei's steady explanatory blocking inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.4s] the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads pauses briefly then composes himself in front of recognizable Democratic Party politicians (resembling Chuck Schumer, Nancy Pelosi, and Elizabeth Warren) face-swapped onto Qing court ministers in dark royal-blue official robes and Republican court officials. [2.4s-14.38s] Speaking briskly to dismiss the insider recommendations, Marco Rubio replies alone in Mandarin Chinese: '有倒是有，不过多数是前CEO一党的人，像科莱特·克雷斯、马拉科夫斯基、杰伊·普里等，他们写的荐章当然不能作数。' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, faint rustle of court beads, muted tense string chord, speaking in Mandarin Chinese with Marco Rubio's exact vocal timbre, sharp rapid high-energy clear tenor-baritone voice and assertive confrontational political debater cadence: '有倒是有，不过多数是前CEO一党的人，像科莱特·克雷斯、马拉科夫斯基、杰伊·普里等，他们写的荐章当然不能作数。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 09（`yz12_huang_shot09`）· 转（突问马斯克）· 特朗普冷冷追问马斯克，鲁比奥秒拒
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`192 帧` / `24 fps` = **`8.00 秒`**（`k=11`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2109`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维））
- **中文台词与本尊音色对齐**：【特朗普】「那么马斯克呢？」 / 【鲁比奥】「马斯克的荐章也不能作数。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 3.2s]：`<Picture 1>`+`<Picture 2>` 特朗普冷不丁抛出一句“那么马斯克呢？”，眼神锐利如刀；
  - [3.2s - 8.00s]：`<Picture 3>` 鲁比奥立刻接招回话“马斯克的荐章也不能作数。”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Marco Rubio portraying Grand Secretary Tong Guowei) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Sharp shot-reverse-shot medium close-up inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-3.2s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads narrows his eyes and asks abruptly in Mandarin Chinese: '那么马斯克呢？' [3.2s-8.0s] Without hesitation, the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads steps slightly closer and answers swiftly in Mandarin Chinese: '马斯克的荐章也不能作数。' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, sudden tense silence, crisp pluck of dramatic strings, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '那么马斯克呢？', speaking in Mandarin Chinese with Marco Rubio's exact vocal timbre, sharp rapid high-energy clear tenor-baritone voice and assertive confrontational political debater cadence: '马斯克的荐章也不能作数。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 10（`yz12_huang_shot10`）· 承（搬出白宫犯上）· 鲁比奥称马斯克十一月十二日在白宫椭圆形办公室狂悖犯上
- **所属幕次与场次**：第一幕：特朗普开场质问荐章 & 鲁比奥正面应对 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2110`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/marco_rubio/ref_marco_rubio_half.png`（鲁比奥（替佟国维） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙））
- **中文台词与本尊音色对齐**：【鲁比奥】「马斯克十一月十二日在白宫椭圆形办公室狂悖犯上，当时就被总统驳斥了，所以他写的荐章也不能作数。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：`<Picture 1>`+`<Picture 2>` 鲁比奥微抬下巴，搬出总统此前驳斥马斯克的旧账；
  - [2.6s - 14.38s]：一口气说完马斯克在白宫椭圆形办公室狂悖犯上之由，`<Picture 3>` 特朗普面无表情冷眼旁观。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Marco Rubio portraying Grand Secretary Tong Guowei), and use <Picture 3> as facial identity reference for the secondary character (Donald Trump portraying the Qing Emperor) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up on Marco Rubio defending his ruling inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.6s] the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads lifts his chin earnestly toward the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads on the dragon throne. [2.6s-14.38s] Delivering his justification cleanly in Mandarin Chinese, Marco Rubio states: '马斯克十一月十二日在白宫椭圆形办公室狂悖犯上，当时就被总统驳斥了，所以他写的荐章也不能作数。' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, quiet murmuring among background Democratic and Republican officials, resonant hall silence, speaking in Mandarin Chinese with Marco Rubio's exact vocal timbre, sharp rapid high-energy clear tenor-baritone voice and assertive confrontational political debater cadence: '马斯克十一月十二日在白宫椭圆形办公室狂悖犯上，当时就被总统驳斥了，所以他写的荐章也不能作数。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 11（`yz12_huang_shot11`）· 转（全场破冰）· 特朗普扫视群臣，贝森特（替张廷玉）独自出列保举黄仁勋
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene01_qianqing_palace`
- **时间网格与规格**：`294 帧` / `24 fps` = **`12.25 秒`**（`k=17`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2111`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉））
- **中文台词与本尊音色对齐**：【特朗普】「你们、你们……你们中间，有没有人推举黄仁勋的？」 / 【贝森特】「有，臣推举的就是黄仁勋。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 5.5s]：`<Picture 1>`+`<Picture 2>` 特朗普起立环视鸦雀无声的满朝两党百官，连声追问有没有人推举黄仁勋；
  - [5.5s - 12.25s]：死寂之中，`<Picture 3>` 佩戴银丝眼镜的贝森特沉稳出列，清朗应道“有，臣推举的就是黄仁勋。”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Scott Bessent portraying Grand Secretary Zhang Tingyu) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Dramatic tracking shot from throne across quiet court to Zhang Tingyu stepping forward inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-5.5s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads sweeps a piercing look over the silent rows of Democratic and Republican face-swapped ministers and asks intensely in Mandarin Chinese: '你们、你们……你们中间，有没有人推举黄仁勋的？' [5.5s-12.25s] Breaking the tense silence, the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge steps calmly out from the ranks, bows with quiet dignity, and answers clearly in Mandarin Chinese: '有，臣推举的就是黄仁勋。' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, heavy silence across the hall, deliberate steady footsteps on stone floor, subtle noble string swell, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '你们、你们……你们中间，有没有人推举黄仁勋的？', speaking in Mandarin Chinese with Scott Bessent's exact vocal timbre, composed refined articulate deep baritone voice and calm Wall Street statesman cadence: '有，臣推举的就是黄仁勋。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 12（`yz12_huang_shot12`）· 承（御前剖白）· 特朗普主动回应外界对“出尔反尔”的猜疑
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`294 帧` / `24 fps` = **`12.25 秒`**（`k=17`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2112`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉））
- **中文台词与本尊音色对齐**：【特朗普】「你们有些事可能会觉得很奇怪，甚至有人会认为朕是出尔反尔。这里，朕要说明一下：」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：`<Picture 1>`+`<Picture 2>` 特朗普神情转为深沉恳切，先向 `<Picture 3>` 贝森特微微颔首；
  - [2.6s - 12.25s]：环顾满朝两党众臣，坦然道出众人以为朕“出尔反尔”的疑虑并准备亲自说明。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Scott Bessent portraying Grand Secretary Zhang Tingyu) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up on the Emperor descending slightly or leaning at the imperial desk inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.6s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads nods subtly toward the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge before turning back to address the hushed assembly. [2.6s-12.25s] Speaking with measured presidential gravity in Mandarin Chinese, the Emperor declares: '你们有些事可能会觉得很奇怪，甚至有人会认为朕是出尔反尔。这里，朕要说明一下：' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, deep palace ambient room tone, warm contemplative orchestral pad, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '你们有些事可能会觉得很奇怪，甚至有人会认为朕是出尔反尔。这里，朕要说明一下：'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 13（`yz12_huang_shot13`）· 承（厘清责任）· 点明废黜CEO系英伟达董事会独断专行，自己当时驻跸海湖庄园
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2113`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/republicans/ref_republicans.png`（共和党人士换脸群臣）
- **中文台词与本尊音色对齐**：【特朗普】「废黜CEO，是英伟达董事会独断专行，事先没有和你们商量。这有几个原因：一是朕当时驻跸海湖庄园，」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.8s]：特朗普摊开双手，明确把罢免风波定性为“英伟达董事会独断专行”；
  - [2.8s - 14.38s]：娓娓道出第一层缘由——当时自己正驻跸海湖庄园，殿下两党百官神色震动。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Republican Party court officials (Mike Johnson, Howard Lutnick, Mitch McConnell, John Thune)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Steady medium shot behind the imperial desk inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.8s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads gestures openly with both palms while recognizable Republican Party politicians (resembling Mike Johnson, Mitch McConnell, and Howard Lutnick) face-swapped onto Qing court officials in crimson-trimmed official robes and Democratic ministers listen in rapt attention. [2.8s-14.38s] Explaining with unmistakable cadence in Mandarin Chinese, the Emperor states: '废黜CEO，是英伟达董事会独断专行，事先没有和你们商量。这有几个原因：一是朕当时驻跸海湖庄园，' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, subtle rustle of imperial yellow silk sleeves, quiet attentive room tone, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '废黜CEO，是英伟达董事会独断专行，事先没有和你们商量。这有几个原因：一是朕当时驻跸海湖庄园，'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 14（`yz12_huang_shot14`）· 承（国运大局）· 阐明当时情形晦暗，为美股AI霸权与美利坚国运先稳大局
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2114`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/democrats/ref_democrats.png`（民主党人士换脸群臣）
- **中文台词与本尊音色对齐**：【特朗普】「事起肘腋之间，许多情形晦暗不明，为美股与AI霸权想、为美利坚国运想，也不得不先稳大局；」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.8s]：镜头沿 缓缓平移，光柱穿过檀香轻烟映亮特朗普肃穆面容；
  - [2.8s - 14.38s]：特朗普沉声阐述为美股与AI霸权、美利坚国运先稳大局的深层考量。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Democratic Party court ministers (Chuck Schumer, Nancy Pelosi, Elizabeth Warren, Hakeem Jeffries)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Slow lateral dolly medium shot across the imperial dais inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.8s] Golden light shafts drift through incense smoke across the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads as recognizable Democratic Party politicians (resembling Chuck Schumer, Nancy Pelosi, and Elizabeth Warren) face-swapped onto Qing court ministers in dark royal-blue official robes and Republican ministers bow their heads slightly. [2.8s-14.38s] Delivering his words with solemn weight in Mandarin Chinese, the Emperor continues: '事起肘腋之间，许多情形晦暗不明，为美股与AI霸权想、为美利坚国运想，也不得不先稳大局；' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, distant resonant palace ambience, slow majestic cello progression, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '事起肘腋之间，许多情形晦暗不明，为美股与AI霸权想、为美利坚国运想，也不得不先稳大局；'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 15（`yz12_huang_shot15`）· 承（回溯风波）· 提及黄仁勋当时风波虽难解，但事后看来大有隐情
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2115`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/jensen_huang/ref_jensen_huang_front.png`（黄仁勋（替太子/CEO））
- **中文台词与本尊音色对齐**：【特朗普】「二是当时黄仁勋的荒诞不经，实在是叫人不可忍，也不可解。但事后看来，他的那些事情，」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 3.0s]：`<Picture 1>`+`<Picture 2>` 特朗普微微皱眉回忆当初风波，语气由严厉渐转宽和；
  - [3.0s - 14.38s]：画面带出 `<Picture 3>` 身披黑皮衣与杏黄龙纹织锦的黄仁勋沉稳身影，特朗普点出“事后看来”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Jensen Huang portraying the Crown Prince CEO) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up on the Emperor with reflective visual framing of the Crown Prince inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-3.0s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads furrows his brow thoughtfully while recalling the crisis surrounding the 61-year-old East Asian visionary looking like Jensen Huang with silver-gray short swept hair and rimless rectangular glasses wearing his signature black leather jacket layered with imperial apricot-yellow dragon silk. [3.0s-14.38s] Speaking with a shifting, more sympathetic presidential cadence in Mandarin Chinese, the Emperor remarks: '二是当时黄仁勋的荒诞不经，实在是叫人不可忍，也不可解。但事后看来，他的那些事情，' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, gentle breath, soft atmospheric woodwind and strings undertone, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '二是当时黄仁勋的荒诞不经，实在是叫人不可忍，也不可解。但事后看来，他的那些事情，'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 16（`yz12_huang_shot16`）· 转（亮出奇折）· 定性黄仁勋遭暗算，举起贝森特奏折赞其写得好
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2116`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉））
- **中文台词与本尊音色对齐**：【特朗普】「有些是捕风捉影、纯属子虚，有的则是著了别人的暗算，才使得一时失察、进退失据。贝森特的折子写得好：」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 3.0s]：`<Picture 1>`+`<Picture 2>` 特朗普从御案抽出那份单独的明黄奏折，目光赞赏地望向 `<Picture 3>` 贝森特；
  - [3.0s - 14.38s]：朗声为黄仁勋定性“捕风捉影、遭人暗算”，正式引出“贝森特的折子写得好：”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Scott Bessent portraying Grand Secretary Zhang Tingyu) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Close-up pushing onto the yellow memorial held by the Emperor inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-3.0s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads lifts a single neatly folded yellow silk memorial from the desk and glances approvingly toward the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge. [3.0s-14.38s] Unfolding the scroll with authoritative satisfaction, the Emperor declares in Mandarin Chinese: '有些是捕风捉影、纯属子虚，有的则是著了别人的暗算，才使得一时失察、进退失据。贝森特的折子写得好：' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, crisp unfolding of yellow silk memorial paper, subtle triumphant brass warmth, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '有些是捕风捉影、纯属子虚，有的则是著了别人的暗算，才使得一时失察、进退失据。贝森特的折子写得好：'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 17（`yz12_huang_shot17`）· 转（高光名句）· 宣读“无心为恶虽恶不罚、退居外部正合外部寻帅之规”
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2117`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/jensen_huang/ref_jensen_huang_front.png`（黄仁勋（替太子/CEO））
- **中文台词与本尊音色对齐**：【特朗普】「所谓无心为恶，虽恶不罚。况且黄仁勋之过因风波所致，如今既已辞职退居外部，正合外部寻帅之规。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：`<Picture 1>`+`<Picture 2>` 特朗普手捧明黄奏折，声如洪钟宣读千古名句“无心为恶，虽恶不罚”；
  - [2.6s - 14.38s]：神转折抛出“既已辞职退居外部，正合外部寻帅之规”，`<Picture 3>` 黄仁勋沉稳笃定，满朝震动。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Jensen Huang portraying the Crown Prince CEO) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Dramatic medium close-up reading the memorial under warm key light inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.6s] Holding the yellow memorial under warm golden light, the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads begins reciting loudly while the 61-year-old East Asian visionary looking like Jensen Huang with silver-gray short swept hair and rimless rectangular glasses wearing his signature black leather jacket layered with imperial apricot-yellow dragon silk stands composed in the palace light. [2.6s-14.38s] Emphasizing every dramatic phrase with unmistakable Trump cadence in Mandarin Chinese, the Emperor reads: '所谓无心为恶，虽恶不罚。况且黄仁勋之过因风波所致，如今既已辞职退居外部，正合外部寻帅之规。' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, subtle gasp of realization from listening officials, stirring orchestral strings, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '所谓无心为恶，虽恶不罚。况且黄仁勋之过因风波所致，如今既已辞职退居外部，正合外部寻帅之规。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 18（`yz12_huang_shot18`）· 承（制度善后）· 宣读“外设首席合规官治其弊，内礼聘归位感其心”
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2118`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉））
- **中文台词与本尊音色对齐**：【特朗普】「伏祈总统念昔日知遇之情、施宽容之道，外则增设首席合规官以制度治其弊，内则礼聘归位以圣意感其心，」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.5s]：`<Picture 1>`+`<Picture 2>` 特朗普继续朗声诵读，殿下 `<Picture 3>` 贝森特神态谦和稳重；
  - [2.5s - 14.38s]：将“增设首席合规官”与“礼聘归位”娓娓道出，句句击中朝局要害。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Scott Bessent portraying Grand Secretary Zhang Tingyu) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium shot cutting between the Emperor reading and Zhang Tingyu listening calmly inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.5s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads continues reading aloud with commanding clarity as the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge stands serenely below the throne dais. [2.5s-14.38s] Projecting his resonant baritone across the hall in Mandarin Chinese, the Emperor recites: '伏祈总统念昔日知遇之情、施宽容之道，外则增设首席合规官以制度治其弊，内则礼聘归位以圣意感其心，' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, gentle rustle of scroll edges, warm dignified orchestral harmony, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '伏祈总统念昔日知遇之情、施宽容之道，外则增设首席合规官以制度治其弊，内则礼聘归位以圣意感其心，'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 19（`yz12_huang_shot19`）· 合（奏折落款点名）· 宣读结尾并高呼“贝森特！”，贝森特恭敬应“臣在！”
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2119`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉））
- **中文台词与本尊音色对齐**：【特朗普】「倘能使黄仁勋重振英伟达、修心向善，则不仅为硅谷之福，亦美利坚与天下股民之福。——贝森特！」 / 【贝森特】「臣在！」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 10.5s]：`<Picture 1>`+`<Picture 2>` 特朗普高声诵完“硅谷之福，亦美利坚与天下股民之福”，合上奏折朗声呼唤“——贝森特！”；
  - [10.5s - 14.38s]：`<Picture 3>` 贝森特立刻恭敬拱手，以沉稳男中音应答“臣在！”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Scott Bessent portraying Grand Secretary Zhang Tingyu) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium shot ending on Zhang Tingyu stepping forward in response inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-10.5s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads closes the yellow silk memorial with satisfaction and calls out proudly in Mandarin Chinese: '倘能使黄仁勋重振英伟达、修心向善，则不仅为硅谷之福，亦美利坚与天下股民之福。——贝森特！' [10.5s-14.38s] the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge bows respectfully and responds in a steady composed baritone in Mandarin Chinese: '臣在！' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, crisp snap of folded silk memorial, solemn court echo, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '倘能使黄仁勋重振英伟达、修心向善，则不仅为硅谷之福，亦美利坚与天下股民之福。——贝森特！', speaking in Mandarin Chinese with Scott Bessent's exact vocal timbre, composed refined articulate deep baritone voice and calm Wall Street statesman cadence: '臣在！'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 20（`yz12_huang_shot20`）· 承（嘉奖贝森特）· 盛赞贝森特书读得好、以美利坚AI江山社稷为重
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2120`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉））
- **中文台词与本尊音色对齐**：【特朗普】「你这个书读得好！好就好在，时刻不忘大局的忠恕之道，与人为善；好就好在时刻以美利坚AI江山社稷为重，」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：`<Picture 1>`+`<Picture 2>` 特朗普面露欣慰，手指 `<Picture 3>` 贝森特连连点头称许；
  - [2.6s - 14.38s]：盛赞其不忘忠恕之道、时刻以美利坚AI江山社稷为重。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Scott Bessent portraying Grand Secretary Zhang Tingyu) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Warm medium close-up praising Zhang Tingyu inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.6s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads gestures warmly with approval toward the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge, who bows humbly in his navy crane-badge court robe. [2.6s-14.38s] Speaking with unmistakable admiration in Mandarin Chinese, the Emperor praises: '你这个书读得好！好就好在，时刻不忘大局的忠恕之道，与人为善；好就好在时刻以美利坚AI江山社稷为重，' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, quiet solemn hall ambience, uplifting warm strings, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '你这个书读得好！好就好在，时刻不忘大局的忠恕之道，与人为善；好就好在时刻以美利坚AI江山社稷为重，'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 21（`yz12_huang_shot21`）· 转（话锋骤寒）· 痛斥趋红踩黑、只顾选票与禄位的政客
- **所属幕次与场次**：第二幕：贝森特独自出列保举黄仁勋 & 特朗普宣读奇折 | `scene02_imperial_desk_memorial`
- **时间网格与规格**：`294 帧` / `24 fps` = **`12.25 秒`**（`k=17`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2121`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维））
- **中文台词与本尊音色对齐**：【特朗普】「而不像有些人，趋红踩黑、见风使舵，想的不是江山社稷，而是他自己的选票与禄位！」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.4s]：`<Picture 1>`+`<Picture 2>` 特朗普笑容瞬间收敛，凌厉目光如利箭般射向 `<Picture 3>` 鲁比奥与两党百官；
  - [2.4s - 12.25s]：厉声讽刺某些人趋红踩黑、想的只是自己的选票与禄位。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Marco Rubio portraying Grand Secretary Tong Guowei) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Sharp whip-tension cut from Emperor's cold gaze to Marco Rubio inside the elevated imperial dragon desk inside Qianqing Palace stacked with yellow silk memorials, ornate bronze incense burner, overlooking rows of Democratic and Republican face-swapped court ministers. [0.0s-2.4s] The warmth vanishes from the face of the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads as his sharp glare locks onto the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads and the surrounding Democratic and Republican ministers. [2.4s-12.25s] Delivering a biting rebuke in Mandarin Chinese, the Emperor warns: '而不像有些人，趋红踩黑、见风使舵，想的不是江山社稷，而是他自己的选票与禄位！' warm amber candle and daylight mix illuminating the yellow silk memorials and the Emperor's face, high-contrast cinematic depth of field. Audio: quiet palace interior ambience, crisp paper rustling of yellow silk memorials, solemn court tension, abrupt halt of warm strings replaced by tense low percussion pulse, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '而不像有些人，趋红踩黑、见风使舵，想的不是江山社稷，而是他自己的选票与禄位！'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 22（`yz12_huang_shot22`）· 起（正面发难）· 质问鲁比奥两百多名两党议员联名折子是如何串联的
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2122`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维））
- **中文台词与本尊音色对齐**：【特朗普】「鲁比奥，这两百多名两党议员联名的折子，是怎么回事？如果没有人居中联络，这么多人就同声一气、众口一词？」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.8s]：`<Picture 1>`+`<Picture 2>` 特朗普拍响桌上联名荐章，当众点名质问 `<Picture 3>` 鲁比奥；
  - [2.8s - 14.38s]：厉声追问两百多名两党议员为何会同声一气、众口一词。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Marco Rubio portraying Grand Secretary Tong Guowei) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Dramatic medium shot confronting Tong Guowei inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.8s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads taps the thick bundle of joint memorials sharply while locking eyes with the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads amidst the tense Democratic and Republican officials. [2.8s-14.38s] Confronting him directly in Mandarin Chinese, the Emperor demands: '鲁比奥，这两百多名两党议员联名的折子，是怎么回事？如果没有人居中联络，这么多人就同声一气、众口一词？' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, sharp thud of stacked memorials on wooden desk, ominous court silence, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '鲁比奥，这两百多名两党议员联名的折子，是怎么回事？如果没有人居中联络，这么多人就同声一气、众口一词？'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 23（`yz12_huang_shot23`）· 承（鲁比奥硬顶）· 辩称居中联络是白宫内阁责任，推举雷内·哈斯乃公意
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2123`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/marco_rubio/ref_marco_rubio_half.png`（鲁比奥（替佟国维） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/democrats/ref_democrats.png`（民主党人士换脸群臣）
- **中文台词与本尊音色对齐**：【鲁比奥】「回总统，居中联络本就是白宫内阁的责任，推举Arm的雷内·哈斯也是白宫内阁和许多两党官员的公意，」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：`<Picture 1>`+`<Picture 2>` 鲁比奥不退反进，挺直脊背硬顶总统质问，身后 `<Picture 3>` 两党换脸百官屏气凝神；
  - [2.6s - 14.38s]：以辩论派凌厉语速声称居中联络是白宫内阁职责、推举Arm的雷内·哈斯乃公意。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Marco Rubio portraying Grand Secretary Tong Guowei), and use the individual faces inside <Picture 3> strictly as facial identity references for the background Qing court ministers (Democratic Party court ministers (Chuck Schumer, Nancy Pelosi, Elizabeth Warren, Hakeem Jeffries)) in a single unified continuous cinema frame (never render split-screen, grid, or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up on Marco Rubio standing defiant before the court inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.6s] the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads squares his shoulders defiantly in front of recognizable Democratic Party politicians (resembling Chuck Schumer, Nancy Pelosi, and Elizabeth Warren) face-swapped onto Qing court ministers in dark royal-blue official robes and Republican court ministers. [2.6s-14.38s] Answering back with forceful political cadence in Mandarin Chinese, Marco Rubio insists: '回总统，居中联络本就是白宫内阁的责任，推举Arm的雷内·哈斯也是白宫内阁和许多两党官员的公意，' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, crisp rustle of court robe sleeves, tense dramatic percussive heartbeat, speaking in Mandarin Chinese with Marco Rubio's exact vocal timbre, sharp rapid high-energy clear tenor-baritone voice and assertive confrontational political debater cadence: '回总统，居中联络本就是白宫内阁的责任，推举Arm的雷内·哈斯也是白宫内阁和许多两党官员的公意，'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 24（`yz12_huang_shot24`）· 转（针锋相对）· 鲁比奥自称无可指责，特朗普大笑讽刺其独代表白宫内阁
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2124`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/marco_rubio/ref_marco_rubio_half.png`（鲁比奥（替佟国维） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙））
- **中文台词与本尊音色对齐**：【鲁比奥】「这些都是为了我美利坚的AI江山社稷，奴才以为无可指责！」 / 【特朗普】「白宫内阁，哈哈……你一个人代表白宫内阁？」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 8.2s]：`<Picture 1>`+`<Picture 2>` 鲁比奥昂首朗声说完“为了美利坚AI江山社稷，奴才以为无可指责！”；
  - [8.2s - 14.38s]：`<Picture 3>` 特朗普冷笑大喝打断：“白宫内阁，哈哈……你一个人代表白宫内阁？”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Marco Rubio portraying Grand Secretary Tong Guowei), and use <Picture 3> as facial identity reference for the secondary character (Donald Trump portraying the Qing Emperor) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Dynamic shot-reverse-shot between Marco Rubio and laughing Trump inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-8.2s] the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads lifts his head boldly and declares in Mandarin Chinese: '这些都是为了我美利坚的AI江山社稷，奴才以为无可指责！' [8.2s-14.38s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads lets out a sharp mocking laugh from the throne and retorts in Mandarin Chinese: '白宫内阁，哈哈……你一个人代表白宫内阁？' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, echoing ironic presidential laugh across the grand palace hall, taut violin sting, speaking in Mandarin Chinese with Marco Rubio's exact vocal timbre, sharp rapid high-energy clear tenor-baritone voice and assertive confrontational political debater cadence: '这些都是为了我美利坚的AI江山社稷，奴才以为无可指责！', speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '白宫内阁，哈哈……你一个人代表白宫内阁？'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 25（`yz12_huang_shot25`）· 承（当庭对质）· 特朗普转问同为内阁大臣的贝森特
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`243 帧` / `24 fps` = **`10.12 秒`**（`k=14`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2125`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉））
- **中文台词与本尊音色对齐**：【特朗普】「贝森特，你也是白宫内阁大臣，你说说鲁比奥有没有居中联络？」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.4s]：`<Picture 1>`+`<Picture 2>` 特朗普目光转向站在一旁的 `<Picture 3>` 贝森特；
  - [2.4s - 10.13s]：点名追问同样身处白宫内阁的贝森特，鲁比奥究竟有没有居中联络。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Scott Bessent portraying Grand Secretary Zhang Tingyu) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium shot panning from the Emperor to Scott Bessent inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.4s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads turns pointedly toward the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge standing calmly among the cabinet ministers. [2.4s-10.13s] Gesturing toward Marco Rubio, the Emperor questions him in Mandarin Chinese: '贝森特，你也是白宫内阁大臣，你说说鲁比奥有没有居中联络？' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, subtle movement of silk robes as officials turn their heads toward Scott Bessent, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '贝森特，你也是白宫内阁大臣，你说说鲁比奥有没有居中联络？'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 26（`yz12_huang_shot26`）· 承（贝森特圆场）· 贝森特老练滴水不漏，先肯定雷内·哈斯并替同僚留余地
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2126`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/scott_bessent/ref_scott_bessent_half.png`（贝森特（替张廷玉） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维））
- **中文台词与本尊音色对齐**：【贝森特】「回总统，鲁比奥和万斯保举雷内·哈斯，那是因为雷内·哈斯确实有过人之处，臣以为这无可厚非；」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：`<Picture 1>`+`<Picture 2>` 贝森特不慌不忙跨前一步，面色沉静地拱手回话，一旁的 `<Picture 3>` 鲁比奥神色紧绷；
  - [2.6s - 14.38s]：贝森特以老练沉稳的华尔街财长男中音，滴水不漏地点出鲁比奥与万斯保举雷内·哈斯。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Scott Bessent portraying Grand Secretary Zhang Tingyu), and use <Picture 3> as facial identity reference for the secondary character (Marco Rubio portraying Grand Secretary Tong Guowei) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium close-up on Zhang Tingyu speaking with measured composure inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.6s] the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge steps forward smoothly and bows while the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads watches warily beside him. [2.6s-14.38s] Speaking with diplomatic precision in Mandarin Chinese, Scott Bessent replies: '回总统，鲁比奥和万斯保举雷内·哈斯，那是因为雷内·哈斯确实有过人之处，臣以为这无可厚非；' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, quiet attentive hall room tone, subtle low strings, speaking in Mandarin Chinese with Scott Bessent's exact vocal timbre, composed refined articulate deep baritone voice and calm Wall Street statesman cadence: '回总统，鲁比奥和万斯保举雷内·哈斯，那是因为雷内·哈斯确实有过人之处，臣以为这无可厚非；'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 27（`yz12_huang_shot27`）· 转（绵里藏针）· 贝森特点出串联系“一时不慎忘了君子不党之训”
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`243 帧` / `24 fps` = **`10.12 秒`**（`k=14`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2127`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/scott_bessent/ref_scott_bessent_front.png`（贝森特（替张廷玉） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/scott_bessent/ref_scott_bessent_half.png`（贝森特（替张廷玉） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/jd_vance/ref_jd_vance_front.png`（万斯（替马齐））
- **中文台词与本尊音色对齐**：【贝森特】「至于众人串联之事，那也是因为一时不慎忘了君子不党的教训。」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.2s]：`<Picture 1>`+`<Picture 2>` 贝森特语锋温和却字字千钧，身旁的 `<Picture 3>` 万斯神色微变；
  - [2.2s - 10.13s]：一锤定音把“众人串联”定性为“忘了君子不党的教训”，既全同僚面子又坐实串联之实。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Scott Bessent portraying Grand Secretary Zhang Tingyu), and use <Picture 3> as facial identity reference for the secondary character (JD Vance portraying Grand Secretary Maci) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Medium two-shot showing Scott Bessent and uneasy JD Vance inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.2s] the 62-year-old silver-haired statesman looking like Scott Bessent wearing refined silver-rimmed glasses and a Qing Dynasty first-rank dark navy court robe with embroidered crane badge maintains a calm diplomatic gaze while the 42-year-old bearded Grand Secretary looking like JD Vance with a neatly trimmed full dark beard and piercing blue eyes wearing a first-rank Qing Dynasty official court robe and red-tasseled court hat shifts uneasily in his official robe. [2.2s-10.13s] Concluding his deftly balanced statement in Mandarin Chinese, Scott Bessent says: '至于众人串联之事，那也是因为一时不慎忘了君子不党的教训。' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, subtle tense rustle among court ranks, resonant hall stillness, speaking in Mandarin Chinese with Scott Bessent's exact vocal timbre, composed refined articulate deep baritone voice and calm Wall Street statesman cadence: '至于众人串联之事，那也是因为一时不慎忘了君子不党的教训。'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 28（`yz12_huang_shot28`）· 转（图穷匕见）· 鲁比奥公开逼问为何国会两党与白宫众臣不能保举雷内·哈斯
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2128`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/marco_rubio/ref_marco_rubio_front.png`（鲁比奥（替佟国维） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/marco_rubio/ref_marco_rubio_half.png`（鲁比奥（替佟国维） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙））
- **中文台词与本尊音色对齐**：【鲁比奥】「奴才岂敢，只是……只是奴才斗胆问一句，为什么国会两党与白宫众臣不能够保举雷内·哈斯？请总统明示！」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.6s]：`<Picture 1>`+`<Picture 2>` 鲁比奥情绪激昂，不顾后果迎向 `<Picture 3>` 特朗普的威压；
  - [2.6s - 14.38s]：当堂高声逼问为什么国会两党与白宫众臣不能保举雷内·哈斯，请总统明示，冲突推至顶点。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Marco Rubio portraying Grand Secretary Tong Guowei), and use <Picture 3> as facial identity reference for the secondary character (Donald Trump portraying the Qing Emperor) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Dramatic low-angle close-up on Marco Rubio challenging the throne inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.6s] the 55-year-old Grand Secretary looking like Marco Rubio with neatly parted dark hair and sharp intense eyes wearing a dark crimson-navy Qing Dynasty first-rank official robe and court beads steps forward with heightened intensity toward the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads, while Democratic and Republican officials hold their breath. [2.6s-14.38s] Speaking with impassioned confrontational energy in Mandarin Chinese, Marco Rubio challenges: '奴才岂敢，只是……只是奴才斗胆问一句，为什么国会两党与白宫众臣不能够保举雷内·哈斯？请总统明示！' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, collective sharp gasp from the court officials, escalating dramatic drums and brass, speaking in Mandarin Chinese with Marco Rubio's exact vocal timbre, sharp rapid high-energy clear tenor-baritone voice and assertive confrontational political debater cadence: '奴才岂敢，只是……只是奴才斗胆问一句，为什么国会两党与白宫众臣不能够保举雷内·哈斯？请总统明示！'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 29（`yz12_huang_shot29`）· 转（老底威慑 & 万斯硬顶）· 特朗普寒声警告，万斯（替马齐）硬着头皮出列附议
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`345 帧` / `24 fps` = **`14.38 秒`**（`k=20`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2129`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/jd_vance/ref_jd_vance_front.png`（万斯（替马齐））
- **中文台词与本尊音色对齐**：【特朗普】「你真要朕把你的老底都掀出来吗？」 / 【万斯】「总统，臣也以为，诸候选人之中，唯雷内·哈斯宜乎立为新CEO……」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 4.8s]：`<Picture 1>`+`<Picture 2>` 特朗普目光如冰，冷冷警告鲁比奥“你真要朕把你的老底都掀出来吗？”；
  - [4.8s - 14.38s]：紧要关头，`<Picture 3>` 万斯（替马齐）硬着头皮出列躬身，用浑厚谨慎男中音附议唯雷内·哈斯宜立为新CEO。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (JD Vance portraying Grand Secretary Maci) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Dramatic shot-reverse-shot between Emperor and Maci stepping out inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-4.8s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads glares down with icy fury and warns in Mandarin Chinese: '你真要朕把你的老底都掀出来吗？' [4.8s-14.38s] Bracing himself under the crushing pressure, the 42-year-old bearded Grand Secretary looking like JD Vance with a neatly trimmed full dark beard and piercing blue eyes wearing a first-rank Qing Dynasty official court robe and red-tasseled court hat steps forward awkwardly from the court ranks and speaks cautiously in Mandarin Chinese: '总统，臣也以为，诸候选人之中，唯雷内·哈斯宜乎立为新CEO……' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, heavy tense silence broken by hesitant footsteps on stone floor, brooding bass swell, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '你真要朕把你的老底都掀出来吗？', speaking in Mandarin Chinese with JD Vance's exact vocal timbre, grounded resonant mid-low baritone voice and cautious calculated political cadence: '总统，臣也以为，诸候选人之中，唯雷内·哈斯宜乎立为新CEO……'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 30（`yz12_huang_shot30`）· 高潮（雷霆震怒）· 特朗普拍案怒斥万斯“朕看你才是真糊涂！”
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`192 帧` / `24 fps` = **`8.00 秒`**（`k=11`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2130`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/jd_vance/ref_jd_vance_front.png`（万斯（替马齐））
- **中文台词与本尊音色对齐**：【特朗普】「刚才卢特尼克说鲁比奥糊涂，朕看你才是真糊涂！」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 2.2s]：`<Picture 1>`+`<Picture 2>` 特朗普雷霆震怒猛拍御案，`<Picture 3>` 万斯与满朝民主党、共和党换脸群臣骇然跪伏；
  - [2.2s - 8.00s]：特朗普直指万斯怒喝“刚才卢特尼克说鲁比奥糊涂，朕看你才是真糊涂！”。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (JD Vance portraying Grand Secretary Maci) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Low-angle explosive dramatic shot on the Emperor slamming the desk inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-2.2s] the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads slams his hand thunderously onto the imperial dragon desk as the 42-year-old bearded Grand Secretary looking like JD Vance with a neatly trimmed full dark beard and piercing blue eyes wearing a first-rank Qing Dynasty official court robe and red-tasseled court hat and rows of Democratic and Republican ministers drop hastily to their knees in terror. [2.2s-8.0s] Pointing sharply down at JD Vance, the Emperor roars in Mandarin Chinese: '刚才卢特尼克说鲁比奥糊涂，朕看你才是真糊涂！' dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, thunderous palm slam on solid wooden desk, collective rustle of kneeling ministers on stone floor, dramatic imperial timpani hit, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '刚才卢特尼克说鲁比奥糊涂，朕看你才是真糊涂！'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

### 分镜 31（`yz12_huang_shot31`）· 合（定鼎收官）· 降万斯两级列贝森特之后，黄仁勋复立大局已定
- **所属幕次与场次**：第三幕：特朗普怒斥联名折子 & 敲打鲁比奥、万斯 | `scene01_qianqing_palace`
- **时间网格与规格**：`294 帧` / `24 fps` = **`12.25 秒`**（`k=17`，严格 ≤ 15.0s） | 分辨率：`1344×768` | Seed：`2131`
- **工作流与绑定多角度参考**：`workflows/minimax_h3_ref2va_multi3_api.json`
  - `<Picture 1>` (`image`)：`characters/trump/ref_trump_front.png`（特朗普（替康熙） · 正面视角）
  - `<Picture 2>` (`image_2`)：`characters/trump/ref_trump_half.png`（特朗普（替康熙） · 第二视角，双图联合锁死 3D 骨相）
  - `<Picture 3>` (`image_3`)：`characters/jensen_huang/ref_jensen_huang_front.png`（黄仁勋（替太子/CEO））
- **中文台词与本尊音色对齐**：【特朗普】「你的罪在于见事昏愦，随声附和！朕降你两级，仍在白宫内阁行走，列在贝森特之后！」
- **L4 镜头内微时间轴拆解**：
  - [0.0s - 8.5s]：`<Picture 1>`+`<Picture 2>` 特朗普居高临下挥手定夺：“你的罪在于见事昏愦，随声附和！朕降你两级，仍在白宫内阁行走，列在贝森特之后！”；
  - [8.5s - 12.25s]：金色光束笼罩大殿，`<Picture 3>` 身披黑皮衣与杏黄龙纹织锦的黄仁勋从容昂首，满朝两党百官俯首震慑，全片在恢弘交响中收束。
- **画面 + 原生 32kHz 立体声中文配音 Prompt**：
  > Use <Picture 1> and <Picture 2> together as multi-angle facial identity references for the primary speaking character (Donald Trump portraying the Qing Emperor), and use <Picture 3> as facial identity reference for the secondary character (Jensen Huang portraying the Crown Prince CEO) in a single unified continuous cinema frame (never render split-screen or collage). Classic Chinese historical palace drama cinematography in the visual style of Yongzheng Dynasty Episode 12. Grand imperial wide-to-medium closing shot inside the grand imperial Qianqing Palace hall with towering vermilion dragon pillars, golden sunlight shafts cutting through incense smoke, and symmetrical rows of Democratic and Republican face-swapped court officials. [0.0s-8.5s] Standing towering behind the dragon desk, the 78-year-old Emperor looking like Donald Trump with signature swept-back golden blonde hair wearing a bright yellow Qing Dynasty imperial dragon robe and court beads delivers his final verdict with commanding presidential hand gestures in Mandarin Chinese: '你的罪在于见事昏愦，随声附和！朕降你两级，仍在白宫内阁行走，列在贝森特之后！' [8.5s-12.25s] As Democratic and Republican ministers remain knelt in hushed awe, golden sunlight illuminates the 61-year-old East Asian visionary looking like Jensen Huang with silver-gray short swept hair and rimless rectangular glasses wearing his signature black leather jacket layered with imperial apricot-yellow dragon silk standing in calm triumph, signaling the CEO's inevitable reinstatement. dramatic imperial palace chiaroscuro lighting, warm golden sunlight against deep crimson and amber interiors, 35mm anamorphic film grain. Audio: deep resonant palace hall room tone, subtle rustle of heavy silk court robes, tense political silence, solemn resonant palace echo, triumphant grand imperial brass and orchestral strings finale, speaking in Mandarin Chinese with Donald Trump's exact vocal timbre, deep raspy resonant baritone voice and distinctive punchy authoritative presidential cadence: '你的罪在于见事昏愦，随声附和！朕降你两级，仍在白宫内阁行走，列在贝森特之后！'
- **Negative Prompt**：
  > `blurry, split screen, collage, picture-in-picture, lip sync mismatch, English speech, distorted face, extra limbs, deformed hands, modern suit without robe, flicker, watermark, low quality`

---

## 四、云端执行与成片合成标准作业命令

1. **核验 7 套多角度人物参考图上云**：确认 `/MyDrive/AI_Video/projects/02_yongzheng_ep12_huang/characters/<id>/` 下 `ref_<id>_front.png` / `ref_<id>_half.png` 与群像参考图均已就位。
2. **A100 80GB 无头批处理直出（仅预热 1 套 Ref2VA 主模型包）**：
   在 `notebooks/02_h100_batch_runner.ipynb` 中配置 `PROJECT_ID = "02_yongzheng_ep12_huang"` 与 `ACTIVE_PACKS = "minimax_h3_ref2va_bf16 minimax_h3_turbo_lora"`。
   - 先抽测前 2 镜验证换脸与中文音色：`--only-tasks yz12_huang_shot01 yz12_huang_shot02`
   - 抽测通过后执行其余 29 镜全量出片并自动释放 A100。
3. **全片双流质检 + EBU R128 响度归一化拼接成片**：
   ```bash
   python scripts/assemble_film.py --project-dir /content/drive/MyDrive/AI_Video/projects/02_yongzheng_ep12_huang
   ```
