from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "profiles/ifrs17"
PDF_DIR = PROFILE_DIR / "source_pdfs"
RAW_DIR = PROFILE_DIR / "raw"
ALIASES_PATH = PROFILE_DIR / "entities/aliases.json"
GRAPH_PATH = PROFILE_DIR / "graph/graph.json"
MANIFEST_PATH = PROFILE_DIR / "corpus_manifest.json"
EVAL_DIR = ROOT / "evals/ifrs17_retrieval"
QUESTIONS_JSON = EVAL_DIR / "questions_ifrs17_mixed100_v0.1.json"
QUESTIONS_MD = EVAL_DIR / "questions_ifrs17_mixed100_v0.1.md"


SOURCES = [
    {
        "name": "IFRS 17 Insurance Contracts",
        "filename": "ifrs-17-insurance-contracts.pdf",
        "url": "https://www.ifrs.org/content/dam/ifrs/publications/pdf-standards/english/2021/issued/part-a/ifrs-17-insurance-contracts.pdf",
        "source_type": "standard",
    },
    {
        "name": "IFRS 17 Effects Analysis",
        "filename": "ifrs-17-effects-analysis.pdf",
        "url": "https://www.ifrs.org/content/dam/ifrs/project/insurance-contracts/ifrs-standard/ifrs-17-effects-analysis.pdf",
        "source_type": "effects_analysis",
    },
    {
        "name": "IFRS 17 Project Summary",
        "filename": "ifrs-17-project-summary.pdf",
        "url": "https://www.ifrs.org/-/media/project/insurance-contracts/ifrs-standard/ifrs-17-project-summary.pdf",
        "source_type": "project_summary",
    },
    {
        "name": "IFRS 17 Fact Sheet",
        "filename": "ifrs-17-factsheet.pdf",
        "url": "https://www.ifrs.org/content/dam/ifrs/project/insurance-contracts/ifrs-standard/ifrs-17-factsheet.pdf",
        "source_type": "fact_sheet",
    },
    {
        "name": "Amendments to IFRS 17 Project Summary",
        "filename": "project-summary-amends-to-ifrs17.pdf",
        "url": "https://www.ifrs.org/content/dam/ifrs/project/amendments-to-ifrs-17/project-summary-amends-to-ifrs17.pdf",
        "source_type": "amendments_summary",
    },
    {
        "name": "Premium Allocation Approach Example",
        "filename": "premium-allocation-approach-example.pdf",
        "url": "https://www.ifrs.org/content/dam/ifrs/supporting-implementation/ifrs-17/premium-allocation-approach-example.pdf",
        "source_type": "implementation_example",
    },
    {
        "name": "Reinsurance Contracts Held Example",
        "filename": "ifrs-17-reinsurance-contract-held-example.pdf",
        "url": "https://www.ifrs.org/-/media/feature/supporting-implementation/ifrs-17/ifrs-17-reinsurance-contract-held-example.pdf",
        "source_type": "implementation_example",
    },
    {
        "name": "IFRS 17 Scope Slides",
        "filename": "ifrs-17-scope-slides.pdf",
        "url": "https://www.ifrs.org/-/media/feature/supporting-implementation/ifrs-17/webinar-ifrs-17-scope/ifrs-17-scope-slides.pdf",
        "source_type": "implementation_material",
    },
]


FACTS = [
    {
        "id": "IFRS17-01",
        "topic": "objective",
        "source_refs": ["IFRS 17:1"],
        "standard_answer": "IFRS 17 establishes principles for the recognition, measurement, presentation and disclosure of insurance contracts.",
        "criteria": [
            {"label": "IFRS 17", "weight": 1, "aliases": ["IFRS 17"]},
            {"label": "recognition measurement presentation disclosure", "weight": 3, "aliases": ["recognition, measurement, presentation and disclosure", "recognition", "measurement", "presentation", "disclosure"]},
            {"label": "insurance contracts", "weight": 1, "aliases": ["insurance contracts", "insurance contract"]},
        ],
        "questions": [
            "What is the objective of IFRS 17?",
            "A colleague says IFRS 17 is only a measurement standard. What broader accounting areas does it establish principles for?",
            "IFRS 17 objective recognition measurement presentation disclosure",
            "When explaining the purpose of IFRS 17 to a new insurance accountant, how would you describe the standard's objective?",
        ],
    },
    {
        "id": "IFRS17-02",
        "topic": "scope",
        "source_refs": ["IFRS 17:3"],
        "standard_answer": "IFRS 17 applies to insurance contracts issued, reinsurance contracts held and investment contracts with discretionary participation features if the entity also issues insurance contracts.",
        "criteria": [
            {"label": "insurance contracts issued", "weight": 2, "aliases": ["insurance contracts it issues", "insurance contracts issued", "insurance contracts"]},
            {"label": "reinsurance contracts held", "weight": 2, "aliases": ["reinsurance contracts it holds", "reinsurance contracts held"]},
            {"label": "investment contracts with discretionary participation features", "weight": 1, "aliases": ["investment contracts with discretionary participation features", "discretionary participation features"]},
        ],
        "questions": [
            "Which contracts are within the scope of IFRS 17?",
            "If an insurer issues insurance contracts and also holds reinsurance, which types of contracts does IFRS 17 tell it to account for?",
            "IFRS 17 scope insurance contracts reinsurance contracts held investment contracts DPF",
            "For a scope assessment under IFRS 17, what are the main categories of contracts that should be considered?",
        ],
    },
    {
        "id": "IFRS17-03",
        "topic": "definition",
        "source_refs": ["IFRS 17 Appendix A"],
        "standard_answer": "An insurance contract transfers significant insurance risk by requiring the issuer to compensate the policyholder if a specified uncertain future event adversely affects the policyholder.",
        "criteria": [
            {"label": "significant insurance risk", "weight": 2, "aliases": ["significant insurance risk", "insurance risk"]},
            {"label": "compensate the policyholder", "weight": 2, "aliases": ["compensate the policyholder", "compensate"]},
            {"label": "uncertain future event", "weight": 1, "aliases": ["uncertain future event", "specified uncertain future event"]},
        ],
        "questions": [
            "How does IFRS 17 define an insurance contract?",
            "What makes a contract an insurance contract rather than just another financial contract under IFRS 17?",
            "insurance contract significant insurance risk compensate policyholder uncertain future event",
            "In IFRS 17 terms, what risk transfer and event condition must be present for a contract to be an insurance contract?",
        ],
    },
    {
        "id": "IFRS17-04",
        "topic": "separation",
        "source_refs": ["IFRS 17:10-13"],
        "standard_answer": "IFRS 17 requires separation of specified embedded derivatives, distinct investment components and distinct goods or non-insurance services from an insurance contract.",
        "criteria": [
            {"label": "embedded derivatives", "weight": 1, "aliases": ["embedded derivative", "embedded derivatives"]},
            {"label": "distinct investment components", "weight": 2, "aliases": ["distinct investment component", "distinct investment components"]},
            {"label": "distinct goods or non-insurance services", "weight": 2, "aliases": ["distinct goods", "distinct non-insurance service", "non-insurance services"]},
        ],
        "questions": [
            "What components can IFRS 17 require an entity to separate from an insurance contract?",
            "When an insurance contract includes investment or service features, what does IFRS 17 say may need to be separated?",
            "IFRS 17 separate embedded derivatives distinct investment component non-insurance services",
            "In a contract unbundling discussion, which embedded or distinct components should be checked before applying IFRS 17 to the remaining insurance component?",
        ],
    },
    {
        "id": "IFRS17-05",
        "topic": "aggregation",
        "source_refs": ["IFRS 17:14-24"],
        "standard_answer": "IFRS 17 groups insurance contracts by portfolios of similar risks managed together and divides them into groups such as onerous, no significant possibility of becoming onerous and remaining contracts.",
        "criteria": [
            {"label": "portfolio similar risks", "weight": 2, "aliases": ["portfolio", "similar risks", "managed together"]},
            {"label": "onerous group", "weight": 1, "aliases": ["onerous", "onerous contracts"]},
            {"label": "no significant possibility of becoming onerous", "weight": 1, "aliases": ["no significant possibility", "becoming onerous"]},
            {"label": "remaining contracts", "weight": 1, "aliases": ["remaining contracts", "remaining"]},
        ],
        "questions": [
            "How does IFRS 17 require insurance contracts to be grouped for measurement?",
            "A portfolio contains contracts with similar risks. What groups does IFRS 17 require an entity to identify within it?",
            "IFRS 17 level of aggregation portfolio onerous no significant possibility remaining contracts",
            "When building the unit of account under IFRS 17, what portfolio and profitability groupings should be considered?",
        ],
    },
    {
        "id": "IFRS17-06",
        "topic": "annual_cohorts",
        "source_refs": ["IFRS 17:22"],
        "standard_answer": "IFRS 17 states that an entity shall not include contracts issued more than one year apart in the same group.",
        "criteria": [
            {"label": "not include", "weight": 1, "aliases": ["not include", "shall not include"]},
            {"label": "more than one year apart", "weight": 3, "aliases": ["more than one year apart", "one year apart"]},
            {"label": "same group", "weight": 1, "aliases": ["same group", "group"]},
        ],
        "questions": [
            "What does IFRS 17 say about grouping contracts issued more than one year apart?",
            "Can contracts issued in periods more than a year apart be placed in the same IFRS 17 group?",
            "IFRS 17 annual cohorts contracts issued more than one year apart same group",
            "When forming IFRS 17 groups, what time-based restriction applies to contracts issued in different years?",
        ],
    },
    {
        "id": "IFRS17-07",
        "topic": "recognition",
        "source_refs": ["IFRS 17:25"],
        "standard_answer": "A group of insurance contracts is recognised from the earliest of the beginning of the coverage period, the date the first payment becomes due and the date the group becomes onerous.",
        "criteria": [
            {"label": "beginning of coverage period", "weight": 2, "aliases": ["beginning of the coverage period", "coverage period"]},
            {"label": "first payment due", "weight": 2, "aliases": ["first payment", "becomes due"]},
            {"label": "group becomes onerous", "weight": 1, "aliases": ["group becomes onerous", "onerous"]},
        ],
        "questions": [
            "When does IFRS 17 require recognition of a group of insurance contracts?",
            "What are the three earliest-date triggers for recognising an IFRS 17 group?",
            "IFRS 17 recognition beginning coverage period first payment due onerous",
            "If coverage has not yet begun but a group has become onerous, what recognition trigger under IFRS 17 becomes relevant?",
        ],
    },
    {
        "id": "IFRS17-08",
        "topic": "initial_measurement",
        "source_refs": ["IFRS 17:32"],
        "standard_answer": "On initial recognition, a group of insurance contracts is measured as the total of fulfilment cash flows and the contractual service margin.",
        "criteria": [
            {"label": "fulfilment cash flows", "weight": 2, "aliases": ["fulfilment cash flows", "fulfillment cash flows"]},
            {"label": "contractual service margin", "weight": 2, "aliases": ["contractual service margin", "CSM"]},
            {"label": "initial recognition", "weight": 1, "aliases": ["initial recognition", "initially measure"]},
        ],
        "questions": [
            "How is a group of insurance contracts initially measured under IFRS 17?",
            "At initial recognition, which two building blocks make up the measurement of a group under IFRS 17?",
            "IFRS 17 initial measurement fulfilment cash flows contractual service margin CSM",
            "When setting up the opening measurement for an IFRS 17 group, what components must be added together?",
        ],
    },
    {
        "id": "IFRS17-09",
        "topic": "fulfilment_cash_flows",
        "source_refs": ["IFRS 17:33"],
        "standard_answer": "Fulfilment cash flows comprise estimates of future cash flows, an adjustment for the time value of money and financial risks, and a risk adjustment for non-financial risk.",
        "criteria": [
            {"label": "future cash flows", "weight": 1, "aliases": ["future cash flows", "estimates of future cash flows"]},
            {"label": "time value of money and financial risks", "weight": 2, "aliases": ["time value of money", "financial risks"]},
            {"label": "risk adjustment for non-financial risk", "weight": 2, "aliases": ["risk adjustment for non-financial risk", "non-financial risk"]},
        ],
        "questions": [
            "What are fulfilment cash flows under IFRS 17?",
            "Which components are included in fulfilment cash flows for an insurance contract group?",
            "fulfilment cash flows future cash flows time value financial risks risk adjustment non-financial risk",
            "When an actuary calculates IFRS 17 fulfilment cash flows, what estimates and adjustments should be included?",
        ],
    },
    {
        "id": "IFRS17-10",
        "topic": "future_cash_flows",
        "source_refs": ["IFRS 17:33-35"],
        "standard_answer": "Future cash flow estimates under IFRS 17 are explicit, unbiased, probability-weighted estimates that incorporate all reasonable and supportable information available without undue cost or effort.",
        "criteria": [
            {"label": "explicit unbiased probability-weighted", "weight": 3, "aliases": ["explicit, unbiased and probability-weighted", "unbiased", "probability-weighted"]},
            {"label": "reasonable and supportable information", "weight": 1, "aliases": ["reasonable and supportable information", "supportable information"]},
            {"label": "without undue cost or effort", "weight": 1, "aliases": ["without undue cost or effort", "undue cost or effort"]},
        ],
        "questions": [
            "What qualities must estimates of future cash flows have under IFRS 17?",
            "How should an entity estimate future cash flows when measuring an IFRS 17 group?",
            "IFRS 17 future cash flows explicit unbiased probability-weighted reasonable supportable undue cost effort",
            "For fulfilment cash flows, what kind of information and probability weighting does IFRS 17 require in the cash flow estimates?",
        ],
    },
    {
        "id": "IFRS17-11",
        "topic": "discount_rates",
        "source_refs": ["IFRS 17:36"],
        "standard_answer": "Discount rates reflect the time value of money, characteristics of the cash flows and liquidity characteristics of the insurance contracts, while excluding factors not relevant to the cash flows.",
        "criteria": [
            {"label": "time value of money", "weight": 1, "aliases": ["time value of money"]},
            {"label": "characteristics of cash flows", "weight": 1, "aliases": ["characteristics of the cash flows", "cash flows"]},
            {"label": "liquidity characteristics", "weight": 2, "aliases": ["liquidity characteristics", "liquidity"]},
            {"label": "exclude irrelevant factors", "weight": 1, "aliases": ["exclude", "not relevant to the insurance contracts"]},
        ],
        "questions": [
            "What should IFRS 17 discount rates reflect?",
            "In setting IFRS 17 discount rates, which contract and cash-flow characteristics matter?",
            "IFRS 17 discount rates time value money cash flow characteristics liquidity exclude irrelevant factors",
            "How should discount rates be selected so that they are consistent with IFRS 17 measurement requirements?",
        ],
    },
    {
        "id": "IFRS17-12",
        "topic": "risk_adjustment",
        "source_refs": ["IFRS 17:37"],
        "standard_answer": "The risk adjustment for non-financial risk reflects the compensation an entity requires for bearing uncertainty about the amount and timing of cash flows arising from non-financial risk.",
        "criteria": [
            {"label": "compensation entity requires", "weight": 2, "aliases": ["compensation that the entity requires", "compensation an entity requires"]},
            {"label": "uncertainty amount and timing", "weight": 2, "aliases": ["uncertainty about the amount and timing", "amount and timing"]},
            {"label": "non-financial risk", "weight": 1, "aliases": ["non-financial risk", "non financial risk"]},
        ],
        "questions": [
            "What does the IFRS 17 risk adjustment for non-financial risk represent?",
            "Why does IFRS 17 include a risk adjustment in fulfilment cash flows?",
            "risk adjustment non-financial risk compensation uncertainty amount timing cash flows",
            "In IFRS 17 measurement, what uncertainty is compensated by the risk adjustment for non-financial risk?",
        ],
    },
    {
        "id": "IFRS17-13",
        "topic": "csm",
        "source_refs": ["IFRS 17:38"],
        "standard_answer": "The contractual service margin represents the unearned profit the entity will recognise as it provides insurance contract services in the future.",
        "criteria": [
            {"label": "contractual service margin", "weight": 1, "aliases": ["contractual service margin", "CSM"]},
            {"label": "unearned profit", "weight": 2, "aliases": ["unearned profit", "unearned"]},
            {"label": "recognise as services provided", "weight": 2, "aliases": ["recognise as it provides", "insurance contract services", "services in the future"]},
        ],
        "questions": [
            "What does the contractual service margin represent under IFRS 17?",
            "Why is the CSM described as unearned profit in IFRS 17?",
            "CSM contractual service margin unearned profit insurance contract services",
            "If an IFRS 17 group is profitable at inception, what balance defers that profit and how is it released?",
        ],
    },
    {
        "id": "IFRS17-14",
        "topic": "onerous_contracts",
        "source_refs": ["IFRS 17:47-52"],
        "standard_answer": "For an onerous group of insurance contracts, IFRS 17 recognises a loss in profit or loss and establishes a loss component of the liability for remaining coverage.",
        "criteria": [
            {"label": "onerous group", "weight": 1, "aliases": ["onerous group", "onerous contracts"]},
            {"label": "loss in profit or loss", "weight": 2, "aliases": ["loss in profit or loss", "recognise a loss"]},
            {"label": "loss component", "weight": 2, "aliases": ["loss component", "liability for remaining coverage"]},
        ],
        "questions": [
            "What happens when a group of insurance contracts is onerous under IFRS 17?",
            "How does IFRS 17 account for a loss-making insurance contract group?",
            "IFRS 17 onerous group loss profit or loss loss component liability remaining coverage",
            "If fulfilment cash flows exceed consideration at initial recognition, what loss accounting does IFRS 17 require?",
        ],
    },
    {
        "id": "IFRS17-15",
        "topic": "subsequent_measurement",
        "source_refs": ["IFRS 17:40"],
        "standard_answer": "Subsequent measurement separates the carrying amount into the liability for remaining coverage and the liability for incurred claims.",
        "criteria": [
            {"label": "liability for remaining coverage", "weight": 2, "aliases": ["liability for remaining coverage", "LRC"]},
            {"label": "liability for incurred claims", "weight": 2, "aliases": ["liability for incurred claims", "LIC"]},
            {"label": "subsequent measurement", "weight": 1, "aliases": ["subsequent measurement", "carrying amount"]},
        ],
        "questions": [
            "How does IFRS 17 split subsequent measurement of a group of insurance contracts?",
            "What are the LRC and LIC in IFRS 17 subsequent measurement?",
            "IFRS 17 subsequent measurement liability for remaining coverage LRC liability for incurred claims LIC",
            "When analysing the carrying amount after initial recognition, which two liabilities does IFRS 17 distinguish?",
        ],
    },
    {
        "id": "IFRS17-16",
        "topic": "coverage_units",
        "source_refs": ["IFRS 17:B119"],
        "standard_answer": "The CSM is recognised in profit or loss based on coverage units that reflect the quantity of benefits provided and the expected coverage duration.",
        "criteria": [
            {"label": "coverage units", "weight": 2, "aliases": ["coverage units", "coverage unit"]},
            {"label": "quantity of benefits", "weight": 2, "aliases": ["quantity of the benefits", "quantity of benefits"]},
            {"label": "expected coverage duration", "weight": 1, "aliases": ["expected coverage duration", "coverage duration"]},
        ],
        "questions": [
            "How are coverage units used to recognise the CSM under IFRS 17?",
            "What do coverage units reflect when releasing the contractual service margin?",
            "IFRS 17 coverage units CSM quantity benefits expected coverage duration",
            "When deciding how much CSM to recognise in a period, what service pattern information do coverage units capture?",
        ],
    },
    {
        "id": "IFRS17-17",
        "topic": "paa",
        "source_refs": ["IFRS 17:53"],
        "standard_answer": "The premium allocation approach may be used if it is a reasonable approximation of the general model or if the coverage period of each contract in the group is one year or less.",
        "criteria": [
            {"label": "premium allocation approach", "weight": 1, "aliases": ["premium allocation approach", "PAA"]},
            {"label": "reasonable approximation", "weight": 2, "aliases": ["reasonable approximation", "approximation"]},
            {"label": "one year or less", "weight": 2, "aliases": ["one year or less", "coverage period"]},
        ],
        "questions": [
            "When can an entity apply the premium allocation approach under IFRS 17?",
            "Why do short-duration contracts often qualify for the PAA?",
            "IFRS 17 PAA premium allocation approach reasonable approximation coverage period one year or less",
            "For a one-year insurance product, what IFRS 17 simplification might be available and why?",
        ],
    },
    {
        "id": "IFRS17-18",
        "topic": "vfa",
        "source_refs": ["IFRS 17:45"],
        "standard_answer": "The variable fee approach applies to insurance contracts with direct participation features, where the entity's obligation is to pay policyholders an amount equal to the fair value of underlying items less a variable fee.",
        "criteria": [
            {"label": "variable fee approach", "weight": 1, "aliases": ["variable fee approach", "VFA"]},
            {"label": "direct participation features", "weight": 2, "aliases": ["direct participation features", "direct participating"]},
            {"label": "fair value of underlying items less variable fee", "weight": 2, "aliases": ["fair value of the underlying items", "variable fee", "underlying items"]},
        ],
        "questions": [
            "What is the variable fee approach under IFRS 17?",
            "Which IFRS 17 contracts use an approach based on the fair value of underlying items less a variable fee?",
            "IFRS 17 VFA variable fee approach direct participation features underlying items fair value variable fee",
            "If policyholders participate directly in underlying items, how does IFRS 17 characterise the entity's fee?",
        ],
    },
    {
        "id": "IFRS17-19",
        "topic": "reinsurance",
        "source_refs": ["IFRS 17:60-70"],
        "standard_answer": "Reinsurance contracts held are accounted for separately from the underlying insurance contracts, and the entity measures the asset for remaining coverage including the CSM for the reinsurance contract held.",
        "criteria": [
            {"label": "reinsurance contracts held", "weight": 2, "aliases": ["reinsurance contracts held", "reinsurance contract held"]},
            {"label": "separately from underlying contracts", "weight": 2, "aliases": ["separately", "underlying insurance contracts"]},
            {"label": "asset for remaining coverage", "weight": 1, "aliases": ["asset for remaining coverage", "CSM"]},
        ],
        "questions": [
            "How are reinsurance contracts held treated under IFRS 17?",
            "Does IFRS 17 offset reinsurance contracts held against the underlying insurance contracts?",
            "IFRS 17 reinsurance contracts held separately underlying insurance contracts asset remaining coverage CSM",
            "For ceded reinsurance, what separate accounting does IFRS 17 require compared with the underlying issued contracts?",
        ],
    },
    {
        "id": "IFRS17-20",
        "topic": "investment_components",
        "source_refs": ["IFRS 17:85"],
        "standard_answer": "IFRS 17 insurance revenue excludes investment components because they are repaid to policyholders even if an insured event does not occur.",
        "criteria": [
            {"label": "insurance revenue excludes", "weight": 2, "aliases": ["insurance revenue", "exclude", "excludes"]},
            {"label": "investment components", "weight": 2, "aliases": ["investment components", "investment component"]},
            {"label": "repaid to policyholders", "weight": 1, "aliases": ["repaid to policyholders", "repaid"]},
        ],
        "questions": [
            "How are investment components treated in IFRS 17 insurance revenue?",
            "Why are investment components excluded from insurance revenue under IFRS 17?",
            "IFRS 17 insurance revenue excludes investment components repaid policyholders",
            "If part of an insurance contract amount must be repaid regardless of an insured event, how does IFRS 17 treat it in revenue?",
        ],
    },
    {
        "id": "IFRS17-21",
        "topic": "presentation",
        "source_refs": ["IFRS 17:78-80"],
        "standard_answer": "IFRS 17 requires separate presentation of portfolios of insurance contracts that are assets and portfolios that are liabilities, and separate presentation of reinsurance contracts held assets and liabilities.",
        "criteria": [
            {"label": "portfolios assets", "weight": 2, "aliases": ["portfolios of insurance contracts issued that are assets", "assets"]},
            {"label": "portfolios liabilities", "weight": 2, "aliases": ["portfolios of insurance contracts issued that are liabilities", "liabilities"]},
            {"label": "reinsurance contracts held", "weight": 1, "aliases": ["reinsurance contracts held", "separately"]},
        ],
        "questions": [
            "What separate presentation does IFRS 17 require for insurance contract portfolios?",
            "How should IFRS 17 portfolios that are assets and liabilities be shown in the statement of financial position?",
            "IFRS 17 presentation portfolios assets liabilities reinsurance contracts held",
            "In financial statement presentation, why can IFRS 17 not simply net all insurance and reinsurance balances together?",
        ],
    },
    {
        "id": "IFRS17-22",
        "topic": "insurance_revenue",
        "source_refs": ["IFRS 17:83"],
        "standard_answer": "Insurance revenue depicts the provision of services arising from a group of insurance contracts at an amount that reflects the consideration to which the entity expects to be entitled.",
        "criteria": [
            {"label": "insurance revenue", "weight": 1, "aliases": ["insurance revenue"]},
            {"label": "provision of services", "weight": 2, "aliases": ["provision of services", "services"]},
            {"label": "consideration expected entitlement", "weight": 2, "aliases": ["consideration", "expects to be entitled", "entitled"]},
        ],
        "questions": [
            "What does insurance revenue depict under IFRS 17?",
            "How does IFRS 17 link insurance revenue to services and expected consideration?",
            "IFRS 17 insurance revenue provision services consideration expects entitled",
            "When explaining IFRS 17 revenue, how should the relationship between services provided and consideration be described?",
        ],
    },
    {
        "id": "IFRS17-23",
        "topic": "finance_income_expenses",
        "source_refs": ["IFRS 17:87"],
        "standard_answer": "Insurance finance income or expenses comprise the change in the carrying amount of insurance contract groups arising from the effect of the time value of money and financial risk.",
        "criteria": [
            {"label": "insurance finance income or expenses", "weight": 2, "aliases": ["insurance finance income or expenses", "insurance finance income", "insurance finance expenses"]},
            {"label": "change in carrying amount", "weight": 1, "aliases": ["change in the carrying amount", "carrying amount"]},
            {"label": "time value of money and financial risk", "weight": 2, "aliases": ["time value of money", "financial risk"]},
        ],
        "questions": [
            "What are insurance finance income or expenses under IFRS 17?",
            "Which changes in insurance contract balances are presented as finance income or expenses?",
            "IFRS 17 insurance finance income expenses carrying amount time value money financial risk",
            "If discount rates or financial assumptions change an IFRS 17 carrying amount, what presentation category is involved?",
        ],
    },
    {
        "id": "IFRS17-24",
        "topic": "disclosure",
        "source_refs": ["IFRS 17:93"],
        "standard_answer": "The disclosure objective of IFRS 17 is for entities to disclose information that helps users assess the effect of insurance contracts on financial position, financial performance and cash flows.",
        "criteria": [
            {"label": "disclosure objective", "weight": 1, "aliases": ["disclosure objective", "disclose information"]},
            {"label": "financial position", "weight": 1, "aliases": ["financial position"]},
            {"label": "financial performance", "weight": 1, "aliases": ["financial performance"]},
            {"label": "cash flows", "weight": 2, "aliases": ["cash flows", "cash flow"]},
        ],
        "questions": [
            "What is the disclosure objective of IFRS 17?",
            "What should IFRS 17 disclosures help users of financial statements assess?",
            "IFRS 17 disclosure objective financial position financial performance cash flows",
            "When designing IFRS 17 notes, what overall effect of insurance contracts should the disclosures explain?",
        ],
    },
    {
        "id": "IFRS17-25",
        "topic": "transition",
        "source_refs": ["IFRS 17:C3-C5"],
        "standard_answer": "On transition, IFRS 17 is applied retrospectively unless impracticable; if full retrospective application is impracticable, an entity applies the modified retrospective approach or the fair value approach.",
        "criteria": [
            {"label": "retrospectively unless impracticable", "weight": 2, "aliases": ["retrospectively", "unless impracticable", "impracticable"]},
            {"label": "modified retrospective approach", "weight": 2, "aliases": ["modified retrospective approach", "modified retrospective"]},
            {"label": "fair value approach", "weight": 1, "aliases": ["fair value approach", "fair value"]},
        ],
        "questions": [
            "What transition approaches does IFRS 17 allow?",
            "If full retrospective application of IFRS 17 is impracticable, what alternatives are available?",
            "IFRS 17 transition retrospective impracticable modified retrospective approach fair value approach",
            "For an insurer adopting IFRS 17 for the first time, how should transition be approached when historical information is incomplete?",
        ],
    },
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build IFRS 17 corpus, benchmark questions, aliases and graph.")
    parser.add_argument("--skip-pdf-extraction", action="store_true")
    args = parser.parse_args(argv)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ALIASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_pdf_extraction:
        write_raw_sources()
    write_aliases()
    questions = build_questions()
    QUESTIONS_JSON.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    QUESTIONS_MD.write_text(render_questions_markdown(questions), encoding="utf-8")
    write_manifest()
    write_graph_if_index_exists()
    print(f"Questions: {QUESTIONS_JSON}")
    print(f"Aliases: {ALIASES_PATH}")
    print(f"Graph: {GRAPH_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


def write_raw_sources() -> None:
    from pypdf import PdfReader

    for source in SOURCES:
        pdf_path = PDF_DIR / source["filename"]
        if not pdf_path.exists():
            raise FileNotFoundError(f"Missing source PDF: {pdf_path}")
        reader = PdfReader(str(pdf_path))
        lines = [
            f"=== {source['name']} | source metadata ===",
            f"Source URL: {source['url']}",
            f"Source Type: {source['source_type']}",
            f"PDF SHA256: {hash_file(pdf_path)}",
            "",
        ]
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = normalize_pdf_text(text)
            if not text.strip():
                continue
            lines.extend(
                [
                    f"=== {source['name']} | page {page_number} ===",
                    f"Source URL: {source['url']}",
                    f"PDF page: {page_number}",
                    "",
                    text,
                    "",
                ]
            )
        raw_path = RAW_DIR / f"{Path(source['filename']).stem}.txt"
        raw_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_aliases() -> None:
    records = {}
    for fact in FACTS:
        add_alias(records, fact["topic"], [fact["topic"].replace("_", " ")], related_terms=fact["source_refs"])
        for criterion in fact["criteria"]:
            add_alias(
                records,
                criterion["label"],
                criterion["aliases"],
                related_terms=[fact["topic"], *fact["source_refs"]],
            )
    extra = [
        ("general measurement model", ["GMM", "general model", "building block approach", "BBA"], ["fulfilment cash flows", "contractual service margin"]),
        ("contractual service margin", ["CSM", "unearned profit"], ["coverage units", "insurance contract services"]),
        ("premium allocation approach", ["PAA"], ["coverage period", "one year or less"]),
        ("variable fee approach", ["VFA"], ["direct participation features", "underlying items"]),
        ("liability for remaining coverage", ["LRC"], ["liability for incurred claims"]),
        ("liability for incurred claims", ["LIC"], ["liability for remaining coverage"]),
        ("risk adjustment for non-financial risk", ["risk adjustment", "RA"], ["uncertainty", "compensation"]),
        ("investment contracts with discretionary participation features", ["DPF", "discretionary participation features"], ["scope"]),
    ]
    for canonical, aliases, related in extra:
        add_alias(records, canonical, aliases, related_terms=related)
    ALIASES_PATH.write_text(json.dumps(list(records.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_questions():
    questions = []
    variants = [
        {
            "answer_style": "factoid",
            "prompt_style": "direct",
            "length_style": "concise_natural",
            "phrasing": "document_similar",
            "user_level": "expert",
        },
        {
            "answer_style": "open_ended",
            "prompt_style": "with_premise",
            "length_style": "verbose_natural",
            "phrasing": "document_distant",
            "user_level": "novice",
        },
        {
            "answer_style": "factoid",
            "prompt_style": "direct",
            "length_style": "short_search_query",
            "phrasing": "document_similar",
            "user_level": "expert",
        },
        {
            "answer_style": "open_ended",
            "prompt_style": "with_premise",
            "length_style": "long_search_query",
            "phrasing": "document_distant",
            "user_level": "novice",
        },
    ]
    for fact in FACTS:
        if len(fact["questions"]) != 4:
            raise ValueError(f"{fact['id']} must have exactly four questions")
        for index, question in enumerate(fact["questions"], start=1):
            questions.append(
                {
                    "id": f"{fact['id']}-V{index}",
                    "fact_id": fact["id"],
                    "topic": fact["topic"],
                    "source_refs": fact["source_refs"],
                    "question": question,
                    "standard_answer": fact["standard_answer"],
                    "criteria": fact["criteria"],
                    **variants[index - 1],
                }
            )
    if len(questions) != 100:
        raise ValueError(f"Expected 100 questions, got {len(questions)}")
    return questions


def write_manifest() -> None:
    manifest = {
        "profile": "ifrs17",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark_version": "IFRS17-RET-ENV-v0.1",
        "source_note": "Downloaded public IFRS Foundation PDFs for local retrieval benchmarking. Do not treat retrieval-only scores as accounting advice or IFRS compliance evidence.",
        "sources": [
            {
                **source,
                "path": str((PDF_DIR / source["filename"]).relative_to(ROOT)),
                "sha256": hash_file(PDF_DIR / source["filename"]),
                "raw_text": str((RAW_DIR / f"{Path(source['filename']).stem}.txt").relative_to(ROOT)),
            }
            for source in SOURCES
        ],
        "questions": str(QUESTIONS_JSON.relative_to(ROOT)),
        "aliases": str(ALIASES_PATH.relative_to(ROOT)),
        "graph": str(GRAPH_PATH.relative_to(ROOT)),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_graph_if_index_exists() -> None:
    chunks_path = PROFILE_DIR / "index/chunks.json"
    alias_records = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    entities = []
    seen_entity_ids = set()
    for record in alias_records:
        entity_id = entity_id_for(record["canonical"])
        if entity_id in seen_entity_ids:
            continue
        seen_entity_ids.add(entity_id)
        entities.append(
            {
                "id": entity_id,
                "name": record["canonical"],
                "type": infer_entity_type(record["canonical"]),
                "aliases": record.get("aliases", []),
            }
        )

    relations = []
    if chunks_path.exists():
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        for fact in FACTS:
            source = entity_id_for(fact["criteria"][0]["label"])
            target = entity_id_for(fact["topic"])
            if source == target:
                target = entity_id_for(f"{fact['topic']} topic")
                if target not in seen_entity_ids:
                    seen_entity_ids.add(target)
                    entities.append({"id": target, "name": f"{fact['topic']} topic", "type": "Topic", "aliases": [fact["topic"].replace("_", " ")]})
            relations.append(
                {
                    "source": source,
                    "type": relation_type_for_topic(fact["topic"]),
                    "target": target,
                    "supporting_chunk_ids": find_supporting_chunks(chunks, fact),
                    "confidence": 0.85,
                }
            )

    GRAPH_PATH.write_text(json.dumps({"entities": entities, "relations": relations}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_supporting_chunks(chunks, fact):
    aliases = []
    for criterion in fact["criteria"]:
        aliases.extend(criterion.get("aliases", []))
    aliases.extend(fact.get("source_refs", []))
    scored = []
    for chunk in chunks:
        text = normalize_match_text(
            f"{chunk.get('parent_title', '')} {chunk.get('title', '')} {chunk.get('content', '')}"
        )
        score = 0
        for alias in aliases:
            normalized_alias = normalize_match_text(alias)
            if normalized_alias and normalized_alias in text:
                score += max(1, min(5, len(normalized_alias) // 8))
        if score:
            scored.append((score, chunk.get("id", "")))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk_id for _score, chunk_id in scored[:5] if chunk_id]


def render_questions_markdown(questions) -> str:
    lines = ["# IFRS 17 Mixed100 Questions", "", "| ID | Topic | Source refs | Standard answer | Question |", "| --- | --- | --- | --- | --- |"]
    for item in questions:
        lines.append(
            f"| {item['id']} | {item['topic']} | {', '.join(item['source_refs'])} | {item['standard_answer']} | {item['question']} |"
        )
    return "\n".join(lines) + "\n"


def add_alias(records, canonical, aliases, related_terms=None):
    canonical = " ".join(str(canonical).split())
    if not canonical:
        return
    record = records.setdefault(
        canonical,
        {"canonical": canonical, "type": infer_entity_type(canonical), "aliases": [], "related_terms": [], "triggers": []},
    )
    for alias in aliases:
        alias = " ".join(str(alias).split())
        if alias and alias != canonical and alias not in record["aliases"]:
            record["aliases"].append(alias)
    for term in related_terms or []:
        term = " ".join(str(term).split())
        if term and term not in record["related_terms"]:
            record["related_terms"].append(term)


def infer_entity_type(name: str) -> str:
    lowered = name.lower()
    if any(term in lowered for term in ("approach", "model", "method")):
        return "MeasurementModel"
    if any(term in lowered for term in ("liability", "asset", "revenue", "income", "expenses")):
        return "FinancialStatementLineItem"
    if any(term in lowered for term in ("disclosure", "presentation")):
        return "DisclosureRequirement"
    if any(term in lowered for term in ("risk", "cash flows", "margin", "component", "units")):
        return "Concept"
    return "Concept"


def relation_type_for_topic(topic: str) -> str:
    if topic in {"scope", "definition", "separation", "aggregation", "annual_cohorts", "recognition"}:
        return "REQUIRES"
    if topic in {"initial_measurement", "fulfilment_cash_flows", "discount_rates", "risk_adjustment", "csm", "subsequent_measurement", "coverage_units", "paa", "vfa"}:
        return "MEASURED_BY"
    if topic in {"presentation", "insurance_revenue", "finance_income_expenses", "disclosure"}:
        return "PRESENTED_AS"
    if topic in {"transition"}:
        return "TRANSITION_RULE_FOR"
    if topic in {"reinsurance", "investment_components", "onerous_contracts"}:
        return "APPLIES_TO"
    return "ASSOCIATED_WITH"


def entity_id_for(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return f"ifrs17:{slug or sha256(str(name).encode()).hexdigest()[:12]}"


def normalize_pdf_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_match_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).lower()


def hash_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
