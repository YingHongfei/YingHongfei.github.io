"""Topic paths derived from conference subject areas or title keywords."""

import re


def rules(*items):
    return [(group, leaf, re.compile(pattern, re.IGNORECASE)) for group, leaf, pattern in items]


VISION = rules(
    ('三维视觉', '场景重建与新视角', r'3d gaussian|splatting|novel.view|nerf|reconstruction|radiance field|3d scene|4d scene'),
    ('三维视觉', '深度与点云', r'depth|point cloud|stereo|lidar|multi.view|monocular|geometry'),
    ('视觉生成', '扩散与图像生成', r'diffusion|image generation|image editing|video generation|text.to.image|3d generation|flow matching'),
    ('图像理解', '检测、分割与跟踪', r'detection|segmentation|tracking|grounding|recognition|localization'),
    ('多模态学习', '视觉语言模型', r'vision.language|multimodal|multi.modal|caption|visual question answering|\bvlm'),
    ('视觉恢复', '增强与复原', r'restoration|super.resolution|denois|deblur|low.light|enhancement'),
    ('视频理解', '视频表征与行为', r'video|action recognition|motion|temporal|dynamic'),
    ('视觉应用', '医学与遥感', r'medical|pathology|satellite|remote sensing|microscop|radiograph|hyperspectral'),
    ('视觉应用', '机器人与自动驾驶', r'robot|autonomous driving|embodied|navigation'),
    ('视觉表征', '训练与适配', r'adapt|learning|representation|transformer|foundation model|efficient'),
)
ML = rules(
    ('智能体', '多智能体与工具使用', r'multi.agent|agents?\b|tool us|embodied|robot|workflow'),
    ('语言模型', '推理与评测', r'\bllms?\b|language models?|chain.of.thought|reasoning|hallucinat|language model agent'),
    ('强化学习', '策略与奖励', r'reinforcement|reward|policy optimization|\bmdps?\b|offline rl|bandit|actor.critic'),
    ('生成模型', '扩散与流模型', r'diffusion|flow matching|score.based|generative|denoising|sampling'),
    ('多模态学习', '视觉语言与音视频', r'vision.language|multimodal|multi.modal|video|speech|text.to.image'),
    ('模型训练', '优化与计算效率', r'optimization|optimiser|optimizer|gradient|quantiz|prun|distill|sparse|scaling|fine.tun'),
    ('表征学习', '图、对比与自监督', r'graph|contrastive|self.supervised|representation|embedding|attention'),
    ('学习理论', '泛化、收敛与统计', r'converg|generalization|generalisation|statistic|theor|regret|bayes|minimax|sample complex'),
    ('可信学习', '隐私、公平与稳健', r'fairness|privacy|private|bias|robust|unlearn|safety|calibrat|uncertainty'),
    ('数据与任务', '时序和科学机器学习', r'time series|forecast|dynamics|causal|protein|molecular|science|physics|climate'),
)
NLP = rules(
    ('语言模型', '推理与对齐', r'language models?|\bllms?\b|reasoning|chain.of.thought|alignment|reward'),
    ('模型评测', '基准、事实性与安全', r'evaluat|benchmark|hallucinat|factual|safety|fairness|bias|robust'),
    ('信息提取', '检索与问答', r'retrieval|question answering|\brag\b|information extraction|entity|relation extraction'),
    ('多语言处理', '翻译与低资源', r'translation|multilingual|cross.lingual|low.resource|language family'),
    ('多模态交互', '对话、语音与视觉语言', r'speech|multimodal|dialog|conversation|vision.language|visual|audio'),
    ('文本建模', '生成、语义与语料', r'summariz|summaris|semantic|corpus|linguistic|text generation|syntactic|dataset'),
)
SYSTEMS = rules(
    ('系统基础设施', '分布式系统与云', r'distributed|cloud|serverless|cluster|data.center|consensus|replicat|datacenter'),
    ('存储与内存', '文件系统、缓存与内存', r'file system|storage|cache|memory|\bssd\b|\bnvme\b|persistent|key.value'),
    ('硬件与加速', '芯片、FPGA 与 GPU', r'fpga|\bgpu|accelerat|processor|microarchitect|chiplet|circuit|hardware|architecture|\bnoc\b|vlsi'),
    ('学习系统', '模型训练与推理系统', r'language model|inference|deep learning|training|\bllms?\b|neural network|machine learning'),
    ('系统调度', '并行计算与资源管理', r'parallel|schedul|resource|runtime|end.to.end|performance|energy|thread|bandwidth'),
    ('系统可靠性', '验证、隔离与容错', r'verification|fault|failure|recover|isolation|debug|reliab|kernel|virtualiz'),
)
NETWORKS = rules(
    ('无线与移动', '无线接入与感知', r'wireless|mobile|satellite|\bwifi\b|5g|6g|\bnr\b|antenna|beamform|iot|backscatter|sensing'),
    ('数据中心网络', '拥塞与传输', r'congestion|traffic|transport|\brdma\b|\btcp\b|data.center|datacenter|packet|throughput'),
    ('网络控制', '路由与资源分配', r'routing|network management|programmable network|allocat|slicing|optimization|sdn'),
    ('网络应用', '边缘、云与实时系统', r'edge|cloud|stream|real.time|video|distributed|federated|delay'),
    ('网络测量', '性能、可观测性与隐私', r'measure|monitor|privacy|network security|resilien|evaluation'),
)
SECURITY = rules(
    ('密码学', '协议、证明与加密', r'cryptograph|zero.knowledge|\bzkp\b|\bmpc\b|encryption|signatur|lattice|key agreement|proof system|commitment|post.quantum'),
    ('系统安全', '隔离、认证与访问控制', r'authentication|authorization|sandbox|isolat|permission|attest|trusted execution|identity| access control'),
    ('软件安全', '漏洞分析与检测', r'vulnerab|malware|fuzz|bug|intrusion|phishing|exploit|code security'),
    ('隐私保护', '隐私计算与匿名化', r'privacy|private|anonym|differentially private|federated|data protection'),
    ('可信机器学习', '模型安全与防御', r'language model|adversarial|poison|backdoor|machine learning|neural|safety|\bllms?\b'),
    ('数据取证', '篡改识别与溯源', r'forensic|watermark|detect|deepfake|authenticity'),
)
SOFTWARE = rules(
    ('智能软件工程', '代码模型与工程智能体', r'\bllms?\b|language model|code generation|code completion|code agent|copilot|software engineering agent|swe.bench'),
    ('程序分析', '检测、修复与测试', r'test|fuzz|fault|repair|bug|static analysis|symbolic execution|debug|regression|refactor'),
    ('形式化方法', '验证与证明', r'formal|verification|verifying|theorem|model checking|semantics|invariant|temporal logic|solver'),
    ('编程语言', '类型、编译器与运行时', r'compiler|compilation|type system|programming language|runtime|concurren|synthesis|optimization'),
    ('开发过程', '实证、维护与质量', r'empirical|developer|maintain|technical debt|review|repository|software quality|requirements|evolution|ecosystem'),
    *[(group, leaf, pattern.pattern) for group, leaf, pattern in SYSTEMS],
)
DATA = rules(
    ('数据库系统', '查询优化与执行', r'query|join|sql|cardinality|transaction|olap|index|database engine|data management'),
    ('信息检索', '搜索、问答与推荐', r'retriev|search|ranking|recommen|question answering|\brag\b|vector database'),
    ('数据挖掘', '图、序列与推荐建模', r'graph|knowledge graph|time series|trajectory|anomaly|clustering|mining|predict'),
    ('数据管理', '数据治理与分析', r'data quality|metadata|provenance|analytics|data integration|lakehouse|stream|storage|data governance'),
    ('智能数据处理', '向量、模型与表格', r'vector|embedding|model|language|learning|structured|table|benchmark'),
)
THEORY = rules(
    ('算法设计', '图与组合优化', r'graph|matching|combinatorial|routing|flow|coloring|cut|optimization'),
    ('复杂性理论', '计算复杂性与证明', r'complexity|computability|proof|logic|automata|finite state|circuit|hardness|satisfiability|lower bound'),
    ('随机算法', '近似、采样与在线算法', r'random|probabil|approxim|sampl|online|regret|stochastic|streaming'),
    ('信息论', '编码、通信与推断', r'coding|channel|capacity|information|entropy|signal|communication|inference'),
    ('量子计算', '量子算法与复杂性', r'quantum'),
)
GRAPHICS = rules(
    ('计算机图形学', '渲染、仿真与几何', r'render|lighting|mesh|simulation|ray.trac|surface|material|geometry|shader|fabrication'),
    ('可视化', '可视分析与交互', r'visualization|visualisation|visual analytics|chart|dashboard|layout|human computer'),
    ('虚拟现实', 'XR、空间交互与感知', r'virtual reality|augmented reality|mixed reality|\bxr\b|headset|presence|haptic|immersive'),
    ('多媒体', '音视频表示与编码', r'compression|codec|audio|image|video|media|signal'),
    *[(group, leaf, pattern.pattern) for group, leaf, pattern in VISION],
)
HCI = rules(
    ('人机交互', '用户体验与设计', r'user|design|interface|usability|experience|interactive|interaction|accessib'),
    ('计算机支持协作', '在线社区与协作系统', r'collaborat|communit|social|online|moderation|crowdsourc|collective|team'),
    ('普适与移动计算', '感知、设备与健康', r'mobile|sensing|sensor|wearable|health|activity|ubiquitous|context.aware|ambient'),
    ('人机协同', '生成式 AI 与工作流', r'\bai\b|\bllms?\b|chatgpt|language model|agents?|machine learning|human.ai'),
    ('沉浸交互', '空间、触觉与扩展现实', r'virtual reality|mixed reality|augmented|\bxr\b|tangible|haptic'),
)
CROSS = rules(
    ('生物信息学', '序列、组学与生物网络', r'genom|rna|protein|molecular|sequence|gene|omics|single.cell|drug'),
    ('Web 与数据', '搜索、系统与社交计算', r'web|retriev|online|network|search|social|recommen|data|graph'),
    ('实时计算', '调度、验证与嵌入式系统', r'real.time|schedul|system|embedded|cyber.physical|verification|timing'),
    ('计算方法', '模型、算法与理论', r'model|learning|optimization|algorithm|theor|analysis'),
)

FAMILIES = {
    '计算机体系结构': ('计算机系统', SYSTEMS), '计算机网络': ('计算机网络', NETWORKS),
    '网络与信息安全': ('网络与信息安全', SECURITY), '软件工程': ('软件工程', SOFTWARE),
    '数据库': ('数据管理与检索', DATA), '计算机科学理论': ('计算机科学理论', THEORY),
    '计算机图形学与多媒体': ('图形学与多媒体', GRAPHICS), '人工智能': ('机器学习', ML),
    '人机交互与普适计算': ('人机交互与普适计算', HCI), '交叉': ('交叉领域', CROSS),
}
OVERRIDES = {
    **dict.fromkeys(('cvpr', 'iccv', 'tpami', 'ijcv'), ('计算机视觉', VISION)),
    'acl': ('自然语言处理', NLP), 'osdi': ('计算机系统', SYSTEMS),
    'sosp': ('计算机系统', SYSTEMS), 'bioinformatics': ('生物信息学', CROSS),
}
OFFICIAL_TERMS = {
    'deep learning': '深度学习', 'large language models': '大语言模型', 'reinforcement learning': '强化学习',
    'deep rl': '深度强化学习', 'general machine learning': '通用机器学习', 'optimization': '优化方法',
    'optimization for deep networks': '深度网络优化', 'learning theory': '学习理论', 'theory': '理论',
    'supervised learning': '监督学习', 'self-supervised learning': '自监督学习', 'generative models': '生成模型',
    'diffusion models': '扩散模型', 'attention mechanisms': '注意力机制', 'graph neural networks': '图神经网络',
    'probabilistic methods': '概率方法', 'applications': '应用', 'language, speech and dialog': '语言、语音与对话',
    'computer vision': '计算机视觉', 'multimodal learning': '多模态学习', 'robotics': '机器人',
    'datasets and benchmarks': '数据集与基准', 'evaluation': '评估', 'representation learning': '表征学习',
    'privacy and security': '隐私与安全', 'privacy': '隐私', 'robustness': '鲁棒性', 'fairness': '公平性',
    'machine learning systems': '机器学习系统', 'everything else': '其他方向', 'other': '其他方向',
    'unsupervised learning': '无监督学习', 'statistics': '统计学', 'causal inference': '因果推断',
    'interpretability': '可解释性', 'graph learning': '图学习', 'online learning': '在线学习',
    'active learning': '主动学习', 'transfer learning': '迁移学习', 'continual learning': '持续学习',
    'sequence models': '序列模型', 'transformers': 'Transformer', 'federated learning': '联邦学习',
    'efficient training': '高效训练', 'efficient inference': '高效推理', 'computer architecture': '计算机体系结构',
}


def classify(paper, venue):
    family = next((spec for key, spec in FAMILIES.items() if venue['domain'].startswith(key)), ('交叉领域', CROSS))
    root, family_rules = OVERRIDES.get(venue['id'], family)
    official = paper.get('officialTopic', '').strip()
    if official:
        parts = [part.strip().replace('/', '／') for part in re.split(r'\s*(?:->|→|\|)\s*', official) if part.strip()]
        translated = [OFFICIAL_TERMS.get(part.casefold(), part) for part in parts]
        if translated:
            if len(translated) == 1:
                applicable_rules = {'计算机视觉': VISION, '自然语言处理': NLP}.get(translated[0], family_rules)
                child = next((group for group, _, expr in applicable_rules if expr.search(paper['title'])), '其他方向')
                if child != translated[0]:
                    translated.append(child)
            return [[root, *translated[:2]]], 'program'

    title = paper['title']
    for group, leaf, pattern in family_rules:
        if pattern.search(title):
            return [[root, group, leaf]], 'title'
    return [[root, '其他主题', '待细分']], 'unclassified'
