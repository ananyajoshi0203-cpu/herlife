# Bloom research notes: cycles, wearables, life stages

Bloom is a lifestyle-record app, not a medical device. Everything below is written so the app can describe patterns and suggest questions for a clinician. Nothing here supports a diagnosis. Each claim carries a numbered citation; see References. Where a threshold is a Bloom product choice rather than a published cutoff, it is labeled **product heuristic**.

---

## 1. The menstrual phases and what counts as a normal cycle

**Plain answer.** In the follicular phase, FSH rises and drives follicle growth, and estradiol climbs as the selected follicle matures; this is the phase that varies most in length [4]. Estradiol peaks, then the LH surge (usually over 36 to 48 hours) triggers release of the egg within about 16 to 32 hours [4]. In the luteal phase the corpus luteum secretes mainly progesterone, which peaks about 6 to 8 days after ovulation; this phase is the most constant, averaging 14 days, and progesterone raises basal body temperature by about 0.5 °C for its duration [4]. Menses follows the rapid fall in progesterone and estrogen when pregnancy does not occur [4]. In app data from 612,613 ovulatory cycles, mean cycle length was 29.3 days, mean follicular phase 16.9 days (95% range 10 to 30) and mean luteal phase 12.4 days (95% range 7 to 17); cycle length fell by about 0.18 days per year between ages 25 and 45 [5]. FIGO 2018 defines normal adult cycles as 24 to 38 days, at most 8 days of bleeding, and a shortest-to-longest variation of at most 7 to 9 days [1, 2]: 9 days or less at ages 18 to 25 and 42 to 45, 7 days or less at ages 26 to 41 [3]. The 2023 PCOS guideline treats cycles under 21 or over 35 days, or fewer than 8 cycles a year, as irregular once a person is more than 3 years past her first period, and any single cycle over 90 days as irregular after the first year [19].

**What Bloom can do with this**
- Use four display phases: menstrual (logged bleeding days), follicular (end of bleeding to estimated ovulation), ovulatory window, luteal (after ovulation to next bleed). Label every phase boundary "estimated".
- Anchor the luteal phase, not the follicular phase: predict the next period as estimated ovulation plus the user's own luteal length (default 12 to 14 days until personal data exists) [4, 5].
- Regularity check over the last 6 or more logged cycles: `max(cycle_len) - min(cycle_len) > 9` for ages 18 to 25 or 42 to 45, `> 7` for ages 26 to 41 → "more variable than the typical range" [1, 3].
- Out-of-range flag: any cycle `< 21` or `> 35` days [19], or `< 24` or `> 38` days [1, 2], shown as a gentle note, never an alarm.
- Copy: "Your cycle length moves around more in the follicular phase. The time after ovulation tends to stay steadier."

**What Bloom must not claim**
- That a cycle outside these ranges is abnormal or a disorder. These are clinical reference ranges, not a verdict.
- That a calendar-estimated phase is the user's true hormonal phase.

---

## 2. What wearables can measure, and how accurately

**Plain answer.** Three signals track the cycle at population level. Skin temperature: in a 22-woman Oura ring pilot, nightly finger skin temperature was about 0.30 °C higher in the luteal than the follicular phase, and the best algorithm detected ovulation with 83.3% sensitivity within a window of 3 days before to 2 days after urine-test-confirmed ovulation; menstruation was detected with 71.9% to 86.5% sensitivity for windows of ±2 to ±4 days [7]. In Apple's prospective cohort (260 participants, 889 cycles), a wrist-temperature algorithm gave a retrospective ovulation estimate for 80.8% of completed cycles that had at least a 0.2 °C temperature signal, with a mean absolute error of 1.22 days and 89.0% of estimates within ±2 days; for ongoing cycles the figures were 80.5% coverage, 1.59 days error and 80.0% within ±2 days [8]. The authors warn that the algorithm can produce an estimate in a cycle where no ovulation occurred, so it should not be used in isolation [8]. Apple's feature needs about two cycles of nightly wear (at least 4 hours a night on 5 nights) and is not for contraception [9]. Resting heart rate and HRV: in WHOOP data from about 11,590 people and 45,000 cycles, population resting heart rate was lowest around cycle day 5 and highest around day 26, while HRV (RMSSD) peaked near day 5 and was lowest near day 27; this fluctuation was smaller in older participants and in those using hormonal birth control [10]. So: wearables can estimate ovulation after the fact with roughly 1 to 2 days of error in cycles with a clear temperature shift. Real-time prospective prediction is less accurate, and no study above validates phase detection in people on hormonal contraception.

**What Bloom can do with this**
- Mark ovulation **retrospectively** only, after a sustained rise in nightly temperature versus the user's own follicular baseline. Require at least 0.2 °C sustained over several nights [8]; if no shift appears, show "no clear temperature shift this cycle" rather than guessing.
- Require two logged cycles of nightly wear before showing any temperature-based estimate [9].
- Show resting HR and HRV as "your body's rhythm across the cycle", expecting HR to be higher and HRV lower before the period [10].
- If the user logs hormonal contraception, turn off temperature-based ovulation estimates and say why [10].
- Copy: "Your temperature rose about 3 nights ago. That often happens after ovulation. This is an estimate, not a test."

**What Bloom must not claim**
- That it predicts or confirms ovulation, or identifies fertile days for avoiding or achieving pregnancy [8, 9].
- Any accuracy figure higher than the studies above, or any accuracy at all for HR or HRV-only phase detection.

---

## 3. Life stages by age band (lifestyle only)

**Plain answer.** Women aged 19 to 50 need 18 mg of iron a day, compared with 8 mg from age 51, and 27 mg in pregnancy [24]. Calcium needs rise from 1,000 mg a day at 19 to 50 to 1,200 mg a day at 51 to 70 [25]. All adults are advised to get 150 to 300 minutes of moderate aerobic activity a week plus muscle-strengthening work for all major muscle groups on 2 or more days [26]. ACOG and ASRM advise that women over 35 who have not conceived after 6 months of trying get an expedited evaluation, because fertility declines with age [27]. Cycles shorten slowly across the mid-reproductive years [5]. Natural menopause usually arrives between 45 and 55 [13]. After menopause, bone density falls and women's lower cardiovascular risk relative to men gradually disappears [13]; the AHA reports that the menopause transition itself is linked with rising LDL cholesterol, more central fat and loss of lean muscle [28].

| Age band | What changes | Lifestyle priorities Bloom can surface |
|---|---|---|
| 18 to 25 | Cycle variation up to 9 days is still within FIGO range [3] | Iron intake (18 mg/day) [24]; calcium 1,000 mg/day [25]; activity and strength habits [26]; adequate fueling if training hard [18] |
| 26 to 34 | Tighter typical regularity (7 days or less) [3] | Same iron and calcium targets [24, 25]; strength 2+ days a week [26]; neutral fertility-timing information if the user opts in [27] |
| 35 to 44 | Cycles keep shortening slowly [5]; over 35, the 6-month guidance applies [27] | Strength and aerobic activity [26]; offer the clinician question about trying to conceive after 6 months [27] |
| 45 to 55 | Menopause transition and menopause typically happen here [11, 13] | Calcium rises to 1,200 mg/day from 51 [25]; iron need drops to 8 mg/day from 51 [24]; strength training and heart-health habits [26, 28] |
| 55+ | Postmenopause; bone and cardiovascular risk become central [13, 28] | Calcium 1,200 mg/day [25]; muscle-strengthening and aerobic activity [26]; any bleeding is a red flag [22] |

**What Bloom can do with this**
- Store age band as a typed field and select nutrition and activity cards from the table. Show the 6-month fertility question only if the user has opted into a "trying to conceive" goal.

**What Bloom must not claim**
- Personalized supplement doses, or that hitting these targets prevents osteoporosis, heart disease or infertility.
- Any statement on fertility odds at a specific age (we could not verify age-specific figures from a primary source, so they are cut).

---

## 4. Perimenopause and menopause

**Plain answer.** STRAW+10 stages reproductive aging by bleeding pattern, with age deliberately excluded as a criterion [11]. Early menopausal transition (stage -2) is a persistent difference of 7 days or more in the length of consecutive cycles, where persistent means it recurs within 10 cycles of the first variable cycle [11]. Late transition (stage -1) is an interval of amenorrhea of 60 days or longer, typically lasts 1 to 3 years, and vasomotor symptoms are likely [11]. Menopause is the final menstrual period, recognized after 12 consecutive months without one [11, 13]; vasomotor symptoms are most likely in early postmenopause [11]. WHO lists hot flushes, night sweats, irregular periods, insomnia, mood changes and vaginal dryness as common symptoms [13]. In the US SWAN cohort the median age at the final menstrual period was 52.5 years [12]; WHO puts most natural menopause at 45 to 55 [13]. Menopause before 45 is early menopause and before 40 is premature [14]; ESHRE's 2024 guideline diagnoses premature ovarian insufficiency in a woman under 40 with at least 4 months of absent or infrequent periods and an FSH above 25 IU/L [15]. On wearables: we found no peer-reviewed validation that consumer wearables detect hot flashes. Older sternal skin conductance monitors agreed with self-reported flashes only 24% of the time in one pilot [16]. Detecting the transition from bleeding logs is feasible because STRAW+10 uses bleeding criteria [11]; wearable temperature is not validated for this.

**What Bloom can do with this**
- For users 45 and over, run the STRAW+10 bleeding checks on logged data:
  - **Early-transition pattern**: two consecutive cycles differ by 7 or more days, and this happens again within the next 10 cycles [11].
  - **Late-transition pattern**: a gap of 60 or more days since the last bleed [11].
  - **12-month mark**: 365 or more days with no logged bleed, which Bloom records as "12 months without a period" [11, 13].
- Let users log hot flashes and night sweats manually, and correlate them with sleep. Do not auto-detect them [16].
- Copy (45+): "Your cycles have varied by a week or more a few times recently. This is a common pattern in the years before menopause. It could be worth asking a clinician about."

**What Bloom must not claim**
- That the user "is in perimenopause" or "has reached menopause". Bloom reports the pattern; a clinician interprets it.
- That a wearable detected a hot flash.
- Any menopause messaging for users under 40 (see section 6). Early or premature menopause and POI are diagnosed by a clinician with blood tests [15].

---

## 5. Irregular cycles that are NOT menopause

**Plain answer.** Many things disrupt cycles. The NHS lists pregnancy, stress, sudden weight loss, being overweight, excessive exercise, hormonal contraception (combined pill, injection, hormonal IUS), breastfeeding, PCOS, thyroid disease and natural variation [20]. The Endocrine Society defines functional hypothalamic amenorrhea as a diagnosis made only after excluding other causes; it suggests evaluation when cycles persistently exceed 45 days or periods are absent for 3 months or more, screening for psychological stressors, and checking TSH, free T4 and prolactin among the first labs [17]. Its treatment centers on correcting energy imbalance (often requiring weight gain) and psychological support, and it advises against using the pill solely to restart periods [17]. The IOC's 2023 consensus treats low energy availability in athletes as a spectrum that becomes harmful (REDs) when it is too severe or lasts too long [18]. A 2024 systematic review of 41 studies found most reported a link between adult psychological stress and menstrual dysfunction, mainly irregular periods and abnormal flow, but no consistent link with abnormal cycle length [23]. Red flags: the NHS advises seeing a doctor after three missed periods in a row [20]; heavy bleeding means changing a pad or tampon every 1 to 2 hours, bleeding over 7 days, or clots larger than about 2.5 cm [21]; bleeding between periods or after sex [21]; and any bleeding after menopause, even once [22].

**What Bloom can do with this**
- **Context flags** (product heuristic; no source sets wearable thresholds for these): compare the 4 weeks before a long or missed cycle against the user's own 90-day baseline.
  - Sleep: average nightly sleep down by an hour or more.
  - Stress load: elevated resting HR and suppressed HRV versus baseline for 7+ days, or high self-reported stress.
  - Training spike: weekly training load up sharply versus the prior 4 weeks.
  - Low energy availability: logged rapid weight loss, or high training load with logged under-eating [17, 18].
- When a context flag coincides with a cycle over 35 days [19] or over 45 days [17], show a "worth discussing" card naming the pattern, never the cause.
- **Prompt-care cards** (sourced): no bleed for 90+ days when not pregnant, postpartum, breastfeeding or on a method that stops bleeding [17, 20]; heavy-bleeding self-report matching [21]; bleeding between periods or after sex [21]; any bleed logged after the 12-month mark [22].
- Copy: "Your last cycle was longer than usual, and your sleep was shorter than your normal in the weeks before. Stress and sleep can both affect cycles. If this continues, it is worth raising with a clinician."

**What Bloom must not claim**
- That stress, sleep, training or diet caused a missed or late period. The evidence is associative [23], and causes must be excluded clinically [17].
- That the user has FHA, REDs, PCOS, thyroid disease or high prolactin.
- That eating more or training less will restore periods, or that the pill will [17].

---

## 6. Decision table for the app

Evaluate rows top to bottom; the first matching row wins, except that **red-flag rows always fire in addition** to any other row. Outputs are a gentle message plus one clinician question. No row outputs a diagnosis.

| # | Inputs (all must match) | Gentle message | Suggested clinician question |
|---|---|---|---|
| R1 | Any age; logged bleed after 12+ months with no bleed [22] | "Bleeding after a year without periods should be checked." | "I had bleeding after 12 months without a period. Can we look into it?" |
| R2 | Any age; heavy-bleeding self-report per [21], or bleeding between periods or after sex [21] | "Heavy or unexpected bleeding is worth getting checked soon." | "My bleeding has been heavier or at unexpected times. What could be causing it?" |
| R3 | Not pregnant, postpartum, breastfeeding, or on a bleeding-suppressing method; 90+ days with no bleed [17, 20] | "It has been 3 months without a period. That is worth checking in about." | "I have not had a period in 3 months. What should we check?" |
| C1 | Pregnant, postpartum or breastfeeding [20] | "Cycle changes are expected right now. Bloom has paused cycle-irregularity notes." | (none unless R1 to R3) |
| C2 | Hormonal contraception logged [10, 20] | "Your bleeding pattern reflects your method. Temperature-based estimates are off." | "Is my current bleeding pattern expected on this method?" (only if pattern changes) |
| A1 | Under 40; cycles outside 21 to 35 days [19] or variability over FIGO limit [1, 3]; context flag present | "Your cycle has been less regular, and [sleep/stress/training] has been different than your usual. These can go together." | "My cycles have become irregular and my [sleep/stress/training] changed. Could that be related, and should anything be checked?" |
| A2 | Under 40; same cycle criteria; no context flag | "Your cycles have varied more than the typical range lately." | "My cycles have been irregular for a few months. What could explain that?" |
| A3 | Under 40; cycles persistently over 45 days [17] | "Your cycles have been running long for a while. A check-in could help." | "My cycles have been longer than 45 days. Should we look at possible causes?" |
| B1 | 40 to 44; irregular per A1 or A2 criteria | "Your cycles have changed recently. Many things can cause this." | "My cycles have changed in my early 40s. Could hormones, stress or something else be involved?" |
| P1 | 45+; early-transition pattern [11] | "Your cycles have varied by a week or more a few times. This is common in midlife." | "My cycle lengths keep changing by a week or more. Could this be the menopause transition?" |
| P2 | 45+; 60+ day gap [11] | "It has been 60+ days since your last period. Longer gaps are common in midlife." | "I am having longer gaps between periods. What should I watch for?" |
| N1 | None of the above | "Your cycle looks steady compared with your recent history." | (none) |

**Hard rules for the implementation**
- Under 40, the strings "menopause", "perimenopause" and "transition" must never appear in output. Add a unit test asserting this for every A-row and red-flag row with age < 40.
- 40 to 44 may mention hormones only as a question, never menopause in the message (early menopause before 45 is a clinical diagnosis [14, 15]).
- No output names a condition (PCOS, FHA, REDs, thyroid, POI) in the message field.
- Users under 18, or within 3 years of their first period, need the adolescent cutoffs (under 21 or over 45 days [19]); if Bloom is 18+ only, still respect "years since first period" when known.

---

## References

1. Munro MG, Critchley HOD, Fraser IS; FIGO Menstrual Disorders Committee. The two FIGO systems for normal and abnormal uterine bleeding symptoms and classification of causes of abnormal uterine bleeding in the reproductive years: 2018 revisions. *Int J Gynaecol Obstet* 2018;143(3):393-408. https://doi.org/10.1002/ijgo.12666
2. Merck Manual Professional Edition. Normal Menstrual Parameters (table, from Munro 2018). https://www.merckmanuals.com/professional/multimedia/table/normal-menstrual-parameters
3. StatPearls. Physiology, Menstrual Cycle. NCBI Bookshelf. https://www.ncbi.nlm.nih.gov/books/NBK500020/
4. McLaughlin JE. Female Reproductive Endocrinology. Merck Manual Professional Edition, reviewed May 2025. https://www.merckmanuals.com/professional/gynecology-and-obstetrics/female-reproductive-endocrinology/female-reproductive-endocrinology
5. Bull JR, Rowland SP, Scherwitzl EB, et al. Real-world menstrual cycle characteristics of more than 600,000 menstrual cycles. *npj Digit Med* 2019;2:83. https://pmc.ncbi.nlm.nih.gov/articles/PMC6710244/
6. (Not used; ACOG Committee Opinion 651 was reviewed but its cycle-length figures could not be verified from primary text, so they were cut.) https://pubmed.ncbi.nlm.nih.gov/26595586/
7. Maijala A, Kinnunen H, Koskimäki H, et al. Nocturnal finger skin temperature in menstrual cycle tracking: ambulatory pilot study using a wearable Oura ring. *BMC Womens Health* 2019;19:150. https://pmc.ncbi.nlm.nih.gov/articles/PMC6883568/
8. Wang Y, et al. Performance of algorithms using wrist temperature for retrospective ovulation day estimate and next menses start day prediction: a prospective cohort study. *Hum Reprod* 2025. https://doi.org/10.1093/humrep/deaf005
9. Apple Support. Receive retrospective ovulation estimates on Apple Watch. https://support.apple.com/120357
10. Jasinski SR, Presby DM, Grosicki GJ, Capodilupo ER, Lee VH. A novel method for quantifying fluctuations in wearable derived daily cardiovascular parameters across the menstrual cycle. *npj Digit Med* 2024;7:373. https://doi.org/10.1038/s41746-024-01394-0
11. Harlow SD, Gass M, Hall JE, et al.; STRAW+10 Collaborative Group. Executive summary of the Stages of Reproductive Aging Workshop + 10. *Menopause* 2012;19(4):387-395. https://pmc.ncbi.nlm.nih.gov/articles/PMC3340903/
12. Gold EB, et al. Factors related to age at natural menopause: longitudinal analyses from SWAN. *Am J Epidemiol* 2013;178(1):70-83. https://academic.oup.com/aje/article/178/1/70/108605
13. World Health Organization. Menopause (fact sheet). https://www.who.int/news-room/fact-sheets/detail/menopause
14. NHS. Early menopause. https://www.nhs.uk/conditions/early-menopause/
15. ESHRE, ASRM, CRE-WHiRL, IMS. Evidence-based guideline: premature ovarian insufficiency (2024). *Hum Reprod Open* 2024;hoae065. https://pubmed.ncbi.nlm.nih.gov/39647506/
16. Pachman DR, et al. Sternal skin conductance: a reasonable surrogate for hot flash measurement? *Menopause* 2013. https://pubmed.ncbi.nlm.nih.gov/23571528/
17. Gordon CM, Ackerman KE, Berga SL, et al. Functional Hypothalamic Amenorrhea: An Endocrine Society Clinical Practice Guideline. *J Clin Endocrinol Metab* 2017;102(5):1413-1439. https://www.endocrine.org/clinical-practice-guidelines/hypothalamic-amenorrhea
18. Mountjoy M, Ackerman KE, Bailey DM, et al. 2023 International Olympic Committee's (IOC) consensus statement on Relative Energy Deficiency in Sport (REDs). *Br J Sports Med* 2023;57(17):1073-1097. https://pubmed.ncbi.nlm.nih.gov/37752011/
19. Teede HJ, et al. International evidence-based guideline for the assessment and management of polycystic ovary syndrome 2023 (summary). https://assets.monashivf.com/assets/Summary-International-evidence-based-guideline-for-the-assessment-and-management-of-polycystic-ovary-syndrome-2023.pdf
20. NHS. Stopped or missed periods. https://www.nhs.uk/conditions/stopped-or-missed-periods/
21. NHS. Heavy periods. https://www.nhs.uk/conditions/heavy-periods/
22. NHS. Postmenopausal bleeding. https://www.nhs.uk/conditions/post-menopausal-bleeding/
23. Poitras M, Shearzad F, Qureshi AF, Blackburn C, Plamondon H. Bloody stressed! A systematic review of the associations between adulthood psychological stress and menstrual cycle irregularity. *Neurosci Biobehav Rev* 2024;163:105784. https://doi.org/10.1016/j.neubiorev.2024.105784
24. NIH Office of Dietary Supplements. Iron: Fact Sheet for Consumers. https://ods.od.nih.gov/factsheets/Iron-Consumer/
25. NIH Office of Dietary Supplements. Calcium: Fact Sheet for Consumers. https://ods.od.nih.gov/factsheets/Calcium-Consumer/
26. US Department of Health and Human Services. Physical Activity Guidelines for Americans, 2nd edition, Executive Summary (2018). https://health.gov/sites/default/files/2019-10/PAG_ExecutiveSummary.pdf
27. ACOG Committee on Gynecologic Practice and ASRM Practice Committee. Female age-related fertility decline. Committee Opinion No. 589. *Obstet Gynecol* 2014;123(3):719-721. https://pubmed.ncbi.nlm.nih.gov/24559617/
28. El Khoudary SR, Aggarwal B, Beckie TM, et al. Menopause transition and cardiovascular disease risk: implications for timing of early prevention. AHA Scientific Statement. *Circulation* 2020;142:e506-e532. https://doi.org/10.1161/CIR.0000000000000912

### Verification notes

- Some primary pages (ACOG, NIA, NIH ODS, PubMed full text) blocked automated fetching. Iron and calcium RDAs [24, 25], the FIGO age bands [3], the Apple accuracy figures [8] and the WHOOP day-of-cycle findings [10] were confirmed through abstracts, archived copies or secondary summaries citing the primary source. Re-check the primary text before quoting numbers in marketing.
- The Menopause Society and NIA pages could not be retrieved; WHO [13], STRAW+10 [11] and SWAN [12] were used instead.
- Cut for lack of verification: hot flash prevalence and duration figures, protein targets by age, age-specific fertility odds, consumer wearable hot flash accuracy, and ACOG's adolescent cycle range.

## Sources at a glance

| Source | Organization | Year | What we use it for |
|---|---|---|---|
| FIGO AUB systems [1, 2, 3] | FIGO | 2018 | Normal cycle 24 to 38 days, variation 7 to 9 days by age |
| Female Reproductive Endocrinology [4] | Merck Manual | 2025 | Hormones by phase, 14-day luteal phase, 0.5 °C BBT rise |
| Bull et al. [5] | Natural Cycles / UCL | 2019 | Real-world phase lengths, cycle shortening with age |
| Maijala et al. [7] | Univ. of Oulu / Oura | 2019 | Finger temperature shift, 83.3% ovulation sensitivity |
| Wang et al. [8], Apple support [9] | Apple / Harvard / NIEHS | 2025 | Retrospective ovulation error 1.22 to 1.59 days; wear requirements |
| Jasinski et al. [10] | WHOOP | 2024 | RHR and HRV pattern across the cycle; muted on birth control |
| STRAW+10 [11] | STRAW+10 group | 2012 | 7-day and 60-day transition criteria, 12-month menopause |
| SWAN [12] | NIH-funded SWAN | 2013 | Median age at final period 52.5 |
| Menopause fact sheet [13] | WHO | current | Age 45 to 55, symptoms, bone and heart risk |
| Early menopause; missed, heavy, postmenopausal bleeding [14, 20, 21, 22] | NHS | current | Early before 45, premature before 40, red flags |
| POI guideline [15] | ESHRE et al. | 2024 | POI: under 40, 4 months, FSH over 25 IU/L |
| FHA guideline [17] | Endocrine Society | 2017 | Over 45 days or 3 months triggers evaluation; energy and stress |
| REDs consensus [18] | IOC | 2023 | Low energy availability as a spectrum |
| PCOS guideline [19] | Monash / international | 2023 | Irregular: under 21 or over 35 days, fewer than 8 a year, over 90 days |
| Stress review [23] | Poitras et al. | 2024 | Stress associated with irregular periods |
| Iron and calcium [24, 25] | NIH ODS | current | RDA by age |
| Physical Activity Guidelines [26] | HHS | 2018 | 150 to 300 min aerobic, strength 2+ days |
| Age-related fertility decline [27] | ACOG / ASRM | 2014 | Over 35: evaluate after 6 months trying |
| Menopause and CVD [28] | AHA | 2020 | Transition-linked cardiometabolic change |

---

## Addendum: seasonal, immunity, and mental health recommendations

These back the "This season" and "Mind and energy" cards on Today. Each card shows its source name in the app.

| Rec in the app | Claim we make | Source |
|---|---|---|
| Get or book a flu shot | Yearly flu vaccine for everyone 6 months and older, ideally by the end of October | CDC, Key Facts About Seasonal Flu Vaccine. https://www.cdc.gov/flu/vaccines/keyfacts.html |
| Protect 7 hours of sleep in flu season | People sleeping under 6 hours were about 4.2 times more likely to develop a cold after viral exposure than those sleeping over 7 | Prather AA, Janicki-Deverts D, Hall MH, Cohen S. Behaviorally Assessed Sleep and Susceptibility to the Common Cold. SLEEP 2015;38(9):1353-1359. https://doi.org/10.5665/sleep.4968 |
| Morning daylight in winter | Shorter days are linked to seasonal low mood; light therapy is a first-line treatment for seasonal affective disorder | NIMH, Seasonal Affective Disorder. https://www.nimh.nih.gov/health/publications/seasonal-affective-disorder |
| Ask about vitamin D as days shorten | Skin makes less vitamin D with less sun; food sources and testing are a clinician conversation | NIH Office of Dietary Supplements, Vitamin D fact sheet. https://ods.od.nih.gov/factsheets/VitaminD-Consumer/ |
| Evening walks in spring | Adults need at least 150 minutes of moderate activity a week | HHS, Physical Activity Guidelines for Americans, 2nd ed. https://health.gov/our-work/nutrition-physical-activity/physical-activity-guidelines |
| Hydrate ahead of heat | Drink before thirst on hot days and schedule exercise in cooler hours | CDC, Heat and Health. https://www.cdc.gov/heat-health/ |
| Keep the bedroom cool | Heat exposure at night increases wakefulness and cuts slow wave and REM sleep | Okamoto-Mizuno K, Mizuno K. Effects of thermal environment on sleep and circadian rhythm. J Physiol Anthropol 2012;31:14. https://doi.org/10.1186/1880-6805-31-14 |
| Track allergy days | Seasonal pollen allergy can disrupt sleep and daytime energy | American Academy of Allergy, Asthma and Immunology. https://www.aaaai.org/ |
| REM and emotions (Mind card) | REM sleep supports overnight processing of emotional experiences | Walker MP, van der Helm E. Overnight therapy? The role of sleep in emotional brain processing. Psychol Bull 2009;135(5):731-748. https://doi.org/10.1037/a0016570 |
| "Body may be fighting something" (future) | Wearable temperature can flag fever onset | Smarr BL et al. Feasibility of continuous fever monitoring using wearable devices. Sci Rep 2020;10:21640. https://doi.org/10.1038/s41598-020-78355-6 |
| Crisis line on the Mind card | 988 Suicide and Crisis Lifeline, call or text 988 in the US | https://988lifeline.org |

**Product rules, not sourced figures:** the "heavy stretch" card shows at 4 or more low or drained mood check-ins in 14 days, or more than 130 high-stress minutes a day on average over 5 days. Energy is the mean of readiness, sleep score, mood, and self-rated energy. Cycle estimates without a logged period use the first cool night after 8 or more nights at or above +0.18 C, consistent with the about 0.3 C luteal shift in the Oura pilot [7].

### Sleep stages, mood, and recovery (Last night's sleep card)

| Claim in the app | Source |
|---|---|
| Typical adult share of sleep: REM about 20 to 25%, deep (slow wave) about 13 to 23% | Sleep Foundation, Stages of Sleep. https://www.sleepfoundation.org/how-sleep-works/stages-of-sleep |
| REM supports overnight emotional processing; less REM can leave reactions to emotional events stronger the next day | Walker MP, van der Helm E. Psychol Bull 2009;135(5):731-748. https://doi.org/10.1037/a0016570 |
| Deep (slow wave) sleep is when most growth hormone is released, supporting physical recovery | Van Cauter E, Leproult R, Plat L. JAMA 2000;284(7):861-868. https://doi.org/10.1001/jama.284.7.861 |

**Product rules:** emotional recharge = REM share / 23% x 85, and physical recovery = deep share / 18% x 85, each capped at 100. Today's mood and energy forecast compares last night's share with her own 30-night average (more than 2 points either way). The mood check-in uses two axes, valence and energy, so anxious and energized both count as high energy, and the "heavy stretch" note counts check-ins with valence 30 or below.
