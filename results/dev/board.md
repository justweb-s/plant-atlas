# Development board: free search / RAG / Plant Atlas

73 questions of `data/cq/dev/`, written from the documents alone. ✓ right · ✗ wrong · ? "I don't know" · a number = partly right.

| | Right | "I don't know" | Wrong | Mean |
|---|---|---|---|---|
| Free search (model + folder of documents) | 59/73 | 0 | 14 | 0.82 |
| Plant Atlas (fact store, reading on demand, judge) | 66/73 | 3 | 4 | 0.92 |

## By group of questions (right / total)

| | DEV-CELL | DEV-IGEA | DEV-IGEB | DEV-REG | DEV-VER |
|---|---|---|---|---|---|
| Free search (model + folder of documents) | 10/13 | 13/13 | 11/16 | 16/18 | 9/13 |
| Plant Atlas (fact store, reading on demand, judge) | 13/13 | 12/13 | 14/16 | 14/18 | 13/13 |

## Question by question

| Question | Expected | Free search | Plant Atlas |
|---|---|---|---|
| DEV-CELL-01: How often must the wear indicator of the load nut of the MA STAR two post lift be checked? | "P6M" | ✓ | ✓ |
| DEV-CELL-02: How often does the manufacturer recommend unpacking and starting up a UR10e robot kept in long-term storage? | "P1Y" | ✓ | ✓ |
| DEV-CELL-03: What mission time (TM, ISO 13849) does the manufacturer state for the nanoScan3 safety laser scanner? | "P20Y" | ✓ | ✓ |
| DEV-CELL-04: For how long does the UR5e manual say to wait after powering the robot off to let it cool down before handling | "PT1H" | ✗ | ✓ |
| DEV-CELL-05: According to the UNIVPM equipment guideline, the written results of the checks on work equipment (such as the  | "P3Y" | ✓ | ✓ |
| DEV-CELL-06: Must the UR10e robot, as delivered by the manufacturer, bear the CE mark under the Machinery Directive? | false | ✓ | ✓ |
| DEV-CELL-07: May the nanoScan3 safety laser scanner be used outdoors? | false | ✓ | ✓ |
| DEV-CELL-08: May the UR10e robot be used without the Teach Pendant attached, provided another emergency stop source is defi | true | ✓ | ✓ |
| DEV-CELL-09: According to the nanoScan3 manual, in which situations (apart from the regular check) must the protective devi | ["Before commissioning", "After changes  | ✗ | ✓ |
| DEV-CELL-10: According to the UR10e manual, who is responsible for the risk assessment of the robot application? | "L'integratore (che può coincidere con l | ✗ | ✓ |
| DEV-CELL-12: How often must the filters of the UR10e Control Box be replaced? | null | ✓ | ✓ |
| DEV-CELL-13: On what date was the last regular thorough check of the cell's nanoScan3 laser scanner carried out? | null | ✓ | ✓ |
| DEV-CELL-14: How often must the UR5e robot arm be recalibrated? | null | ✓ | ✓ |
| DEV-IGEA-01: Given that the company works in mining areas (extractive sector), how often must the IGEA-PRIM 5t overhead tra | "P2Y" | ✓ | ✓ |
| DEV-IGEA-02: Given that the company works in mining areas (extractive sector), how often must the DEFRIES-TITANO overhead t | "P1Y" | ✓ | ✓ |
| DEV-IGEA-03: How often must the AMCO VEBA hydraulic truck-mounted crane at position 4, whose capacity is only 520 kg, be ve | "P1Y" | ✓ | ✓ |
| DEV-IGEA-04: If the JCB JS190NLC mobile crane at position 18 were used under regular conditions, i.e. outside the construct | "P1Y" | ✓ | ✓ |
| DEV-IGEA-06: If the IGEA-PRIM 5t overhead travelling crane at position 13 were used under regular conditions, i.e. outside  | "P3Y" | ✓ | ✓ |
| DEV-IGEA-07: If the GUTTER overhead travelling crane at position 10 were used under regular conditions, i.e. outside the co | "P2Y" | ✓ | ✓ |
| DEV-IGEA-08: Which positions of the list are the lifting devices located in the municipality of Lula (Sos Enattos mine)? | ["6", "23"] | ✓ | 0.67 |
| DEV-IGEA-09: With what minimum notice must the appointed verifier communicate to IGEA the planning of the checks on the dev | "P15D" | ✓ | ✓ |
| DEV-IGEA-10: For the verification operations, must IGEA also make the measuring instruments available to the verifier? | false | ✓ | ✓ |
| DEV-IGEA-11: The verifications covered by the IGEA technical sheet are periodic verifications after the first one: under th | "ASL, entro 30 giorni dalla richiesta" | ✓ | ✓ |
| DEV-IGEA-12: During the periodic verification of the P&H R200 mobile crane at position 17, must the employer show the resul | true | ✓ | ✓ |
| DEV-IGEA-13: On what date was the last periodic verification of the DEMAG overhead travelling crane at position 9 carried o | null | ✓ | ✓ |
| DEV-IGEA-14: As of 14 November 2026, is the periodic verification of the P&H R200 mobile crane at position 17 overdue? | null | ✓ | ✓ |
| DEV-IGEB-01: Given that the company works in mining areas (extractive sector), how often must the IGEA-PRIM 5t overhead tra | "P2Y" | ✗ | ✓ |
| DEV-IGEB-02: Given that the company works in mining areas (extractive sector), how often will the IGEA-PRIM 5t overhead tra | "P1Y" | ✓ | ✓ |
| DEV-IGEB-03: If the 1500 kg FASSI F 28 B22 hydraulic truck-mounted crane at position 3 had been used under regular conditio | "P2Y" | ✓ | ✓ |
| DEV-IGEB-04: If the 1500 kg FASSI F 28 B22 hydraulic truck-mounted crane at position 3 had been used under regular conditio | "P1Y" | ✓ | ✓ |
| DEV-IGEB-05: Given that the company works in mining areas (extractive sector), how often will the Effer hydraulic truck-mou | "P1Y" | ✓ | ✓ |
| DEV-IGEB-06: If the IGEA-PRIM 5t overhead travelling crane at position 13 were used under regular conditions, i.e. outside  | "P2Y" | ✗ | ✓ |
| DEV-IGEB-07: Given that the company works in mining areas (extractive sector), how often must the KITO KR50L electric hoist | "P1Y" | ✓ | ✓ |
| DEV-IGEB-08: Given that the company works in mining areas (extractive sector), how often must the 35,000 kg GCB 35 gantry c | "P1Y" | ✓ | ✓ |
| DEV-IGEB-09: If the 10,000 kg SIS PROFI 10 TI pneumatic hoist at position 14 were used under regular conditions, i.e. outsi | null | ✗ | ✗ |
| DEV-IGEB-10: Which positions of the list are devices whose year of construction is earlier than 1990? | ["8", "9", "10", "11", "12", "17", "23"] | ✓ | ✓ |
| DEV-IGEB-11: Which positions of the list are devices with a capacity below 1,000 kg? | ["2", "4", "5", "6", "7", "24"] | 0.67 | ✓ |
| DEV-IGEB-12: According to Annex B, which positions of the list have Monteponi as their location (sector/service)? | ["13", "14"] | ✓ | ? |
| DEV-IGEB-13: The technical sheet requires IGEA to make available to the verifier, for devices more than 20 years old, the c | ["1", "2", "4", "5", "6"] | ✗ | ✓ |
| DEV-IGEB-14: The verifications of the IGEA devices are entrusted to an authorised body: under the Ministerial Decree of 11  | "P10Y" | ✓ | ✓ |
| DEV-IGEB-15: What is the registration plate of the truck on which the Effer hydraulic crane at position 7 is mounted? | null | ✓ | ✓ |
| DEV-IGEB-16: What amount in euro is paid to the verifier for the periodic verification of the 35,000 kg gantry crane at pos | null | ✓ | ✓ |
| DEV-REG-01: A machine was built and its EC declaration of conformity signed on 10 January 2027, but it is made available o | "Il Regolamento (UE) 2023/1230" | ✓ | ✓ |
| DEV-REG-02: On 1 December 2026 the manufacturer of a machine in a category listed in Annex IV to Directive 2006/42/EC, not | false | ✓ | ✓ |
| DEV-REG-03: On 1 December 2026, for Annex IV categories of Directive 2006/42/EC built to harmonised standards covering all | ["Removable mechanical transmission devi | ✓ | ? |
| DEV-REG-04: On 1 March 2027 a company that is neither the original manufacturer nor a non-professional user carries out a  | "Come fabbricante (as manufacturer), con | ✓ | ✓ |
| DEV-REG-05: The UNIVPM equipment guideline states that the manufacturer is obliged to supply the instructions for use on p | true | ✓ | ✓ |
| DEV-REG-06: On 1 March 2027 a distributor is about to make a machine (not partly completed machinery) available on the mar | ["The machinery bears the CE marking", " | ✗ | 0.25 |
| DEV-REG-07: What is the last day on which a machine can be placed on the market in conformity with Directive 2006/42/EC so | "2027-01-19" | ✓ | ✓ |
| DEV-REG-08: Article 54 of Regulation (EU) 2023/1230 sets several dates of application. From which date does Article 6(7) ( | "2023-07-19" | ✓ | ✓ |
| DEV-REG-09: By which date must the Commission submit the second specific report on the assessment of Article 6(4) and (5)  | "2031-07-20" | ✓ | ✓ |
| DEV-REG-10: As of today (14 November 2026), has the time limit within which the Commission must draw up the report on the  | false | ✓ | ✓ |
| DEV-REG-11: May the UR10e arm of the cell be put into service on the sole basis of the declaration supplied by its manufac | false | ✓ | ✓ |
| DEV-REG-12: The UR5e manual contains a Declaration of Incorporation and the robot's assembly instructions. Once the robot  | "Del fascicolo tecnico della macchina fi | ✓ | ✓ |
| DEV-REG-13: Today (14 November 2026) the integrator completes the robot cell with the UR5e and UR10e arms. According to th | ["Ensure it satisfies the essential heal | 0.50 | 0.50 |
| DEV-REG-14: The manual of the MA STAR two post lift carries an EC declaration of conformity to Directive 2006/42/EC. For a | true | ✓ | ? |
| DEV-REG-15: What is the maximum amount of the penalty applicable in Italy, on 1 February 2027, to a manufacturer infringin | null | ✓ | ✓ |
| DEV-REG-16: On which date did the Commission actually adopt the first implementing act with the template for Member States | null | ✓ | ✓ |
| DEV-REG-17: Which notified body carried out the EC type-examination of the MA STAR two post lift? | null | ✓ | ✓ |
| DEV-REG-18: On what date was the EC declaration of conformity of the complete robot cell (the final machine into which the | null | ✓ | ✓ |
| DEV-VER-01: From which date does Article 50(1) of Regulation (EU) 2023/1230 (Member States' duty to lay down penalties) ap | "2026-10-20" | ✗ | ✓ |
| DEV-VER-02: From which date do Articles 26 to 42 of Regulation (EU) 2023/1230 (notification of conformity assessment bodie | "2024-01-20" | ✓ | ✓ |
| DEV-VER-03: By which date must Member States provide for the first time the data and information referred to in Article 6( | "2025-07-20" | ✓ | ✓ |
| DEV-VER-04: By which date must the Commission submit its first report on the evaluation and review of Regulation (EU) 2023 | "2028-07-20" | ✗ | ✓ |
| DEV-VER-05: On 18 January 2027, is Directive 2006/42/EC still in force (not yet repealed)? | true | ✓ | ✓ |
| DEV-VER-06: On 1 September 2026, does Article 50(1) of Regulation (EU) 2023/1230 (rules on penalties) already apply? | false | ✗ | ✓ |
| DEV-VER-07: On 15 July 2023, did Chapter VI of Regulation (EU) 2023/1230 already apply, instead of Article 11 of Directive | false | ✓ | ✓ |
| DEV-VER-08: A machine was placed on the market on 15 January 2027 in conformity with Directive 2006/42/EC. On 1 March 2027 | true | ✓ | ✓ |
| DEV-VER-09: For the periodic verifications after the first one of Annex VII equipment, is the employer obliged to apply to | false | ✗ | ✓ |
| DEV-VER-10: The Ministerial Decree of 11 April 2011 names INAIL as holder of the first periodic verification and the ASL f | true | ✓ | ✓ |
| DEV-VER-11: After the repeal of Directive 2006/42/EC, until when do EC type-examination certificates issued under Article  | "Fino alla loro scadenza (until they exp | ✓ | ✓ |
| DEV-VER-12: By which date must the Commission adopt the delegated acts provided for in Article 6(11) of Regulation (EU) 20 | null | ✓ | ✓ |
| DEV-VER-13: Within what time limit must the ministerial decree amending the list of equipment in Annex VII, provided for b | null | ✓ | ✓ |
