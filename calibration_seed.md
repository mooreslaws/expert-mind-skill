# Calibration Seed — Skill Enricher Judge

**Purpose:** tune the LLM-judge that decides which content enters an expert skill (YES) vs gets discarded (NO). Items in the BORDERLINE zone exist to calibrate the confidence threshold (target: ~0.7).

**Sources:** personal_wiki/articles + Notion Snipd database (podcast snippets).

**Authors sampled:** Eric Seufert (Mobile Dev Memo), Hannah Parvaz (Aperture), Daphne Tideman (Growth Waves), Larissa Morimoto (PhotoRoom), Adam Hadi (Current), David George (a16z), Sebastian Siemiatkowski (Klarna).

**How to use this file:** scan each example, flip the `Label` if you disagree, add notes inline. Target: ≥45/50 should match your judgment after one pass. If less — judge prompt needs more constraints or you need a different threshold.

---

## YES — belongs in skill (35 examples)

### Eric Seufert — Mobile Dev Memo

**#1. Seufert (Prosperous Society Ep.1)**
> "Each era's economic anxiety reflects its dominant constraint. Food in Malthus's time, allocation in Galbraith's, and distribution in the contemporary environment. The efficiency benefits posed by AI-enhanced development tools shift constraints from production to distribution, whereby human attention becomes the scarce resource in competition."
**Label:** YES
**Why:** Original thesis with historical scaffolding. Defensible point-of-view, not common knowledge.

**#2. Seufert (Prosperous Society Ep.1)**
> "Digital advertising is not broadly an exercise in persuasion. Digital ads don't attempt to convince the median consumer to purchase something they never previously considered buying. It is about identifying the rare consumer whose latent willingness to spend makes the exposure economically rational. The most sophisticated advertising platforms are spending vast sums of money on doing just that."
**Label:** YES
**Why:** Reframes a popular misconception. Foundational worldview claim of Seufert's work.

**#3. Seufert (Prosperous Society Ep.1)**
> "The Millionaire's Mall: imagine the average net worth of shoppers in a mall is $50M. Two interpretations: everyone is wealthy, or one billionaire is present. Targeting does not need to produce a uniform uplift — it needs to shift the distribution enough that the tail contains sufficient value to justify the spend. Conversions are rare because the conditions for conversion are rare."
**Label:** YES
**Why:** Named mental model. Reusable analogy with economic logic.

**#4. Seufert (Prosperous Society Ep.1)**
> "Generative AI is deflationary for content production but inflationary for distribution. Yes, creative becomes cheaper for existing advertisers. But critically, participation expands — more businesses can run ads. The auction clears at the willingness to pay of the marginal bidder, so as more advertisers join, the clearing price rises. That movement progressively prices lower-LTV products out of scalable paid distribution."
**Label:** YES
**Why:** Counter-intuitive prediction with explicit mechanism (auction dynamics). Tradable for forecasting.

**#5. Seufert (Prosperous Society Ep.1)**
> "Bid against true lifetime value to let platforms optimize. The advertiser bids based on expected lifetime value, and the platform assumes the risk of wasted impressions and seeks to minimize it through better prediction. The platform's incentive is to refine its predictions continuously — the more accurately it can identify high-value users, the more budget it can capture."
**Label:** YES
**Why:** Operational principle. Directly actionable for any advertiser.

**#6. Seufert (AppLovin Q1 2026 article)**
> "Almost all new games and a lot of these older games are really looking at this hybrid strategy. At any given time inside a mobile game, sub-10% of the population will pay in a short window. Hybrid monetization 10x the market opportunity for the same customer."
**Label:** YES (from Seufert's framing of the underlying logic, even though quoting the CEO)
**Why:** Articulates the unit-economic logic of hybrid monetization. Mental model, not news.

**#7. Seufert (Meta location fees)**
> "This will complicate bid pricing: while these fees essentially serve as a drag on ROAS, reducing bids by the location tax percentage will not perfectly preserve ROAS, because the bid itself influences delivery and pricing dynamics. So advertisers will need to approach this as a separate optimization problem and either analytically or iteratively calculate the maximum bid that achieves their ROAS target for that geography."
**Label:** YES
**Why:** Tactical reasoning, not news. Names a non-obvious second-order effect.

**#8. Seufert (Meta location fees)**
> "Meta may be attempting to reignite the stalled DST negotiations by passing these fees on to its millions of advertisers, creating a visible tax on advertising spend. Recall that Mark Zuckerberg likened EU fines on US technology companies to tariffs."
**Label:** YES
**Why:** Political/strategic interpretation — Seufert's signature analytical move (read corporate actions as geopolitics).

### Hannah Parvaz — Aperture / Growth Gems #144

**#9. Parvaz**
> "Content-based apps have a significant SEO advantage through programmatic page creation. If your app contains recipes, workouts, book summaries, or similar content, creating thousands of indexed pages around this content can drive substantial organic growth at scale. Runna is the example — they built thousands of programmatic running pages."
**Label:** YES
**Why:** Conditional rule (if X type of app → Y move). Reusable.

**#10. Parvaz**
> "Treat paid acquisition as a funnel accelerator, not your entire growth strategy. The most successful apps combine paid ads with organic social, partnerships, and referral loops. Use paid spend to amplify existing growth engines rather than as a standalone channel."
**Label:** YES
**Why:** Strategic stance. Implicit critique of common practice.

**#11. Parvaz**
> "Don't start with creative volume. Scale creative volume gradually through a decision tree approach. Start with 4-8 themed creatives, extract learnings, branch out based on what works, and only scale to hundreds of creatives once you've built a clear learning path."
**Label:** YES
**Why:** Methodology (decision tree). Named process.

**#12. Parvaz**
> "Meta attribution is always the worst-case scenario in terms of app campaign attribution. Use custom product pages (at least one across app campaigns) and MMPs to triangulate reality and avoid over-pessimistic decision-making. In 100% of cases, Hannah has seen actual installs exceed Meta's reporting."
**Label:** YES
**Why:** Strong claim with empirical backing ("100% of cases"). Reframes how to read data.

**#13. Parvaz**
> "A 12% click-to-install rate destroys your entire funnel economics. Benchmark minimum is 30%, with 60-80% achievable through custom product pages. Fixing app store conversion is often the highest-leverage optimization because it multiplies the effectiveness of every dollar spent on acquisition."
**Label:** YES
**Why:** Quantified threshold + leverage argument. Decision-shaping.

**#14. Parvaz**
> "Start creative strategy with customer psychology, not brainstorming. Use behavior analysis, jobs-to-be-done framework, and psychographic research to identify themes before creating any ads. This research-first approach ensures your creative tests are grounded in actual user motivations."
**Label:** YES
**Why:** Process principle. "X before Y" structure typical of expert heuristics.

**#15. Parvaz**
> "Match your starting channel to your product's natural discovery pattern. High search volume products should start with Google Search (combined with web flows for attribution). Visual/entertainment products may be TikTok-first. Let your product's natural user behavior guide channel selection."
**Label:** YES
**Why:** Decision rule with worked examples.

### Daphne Tideman — Growth Waves / Growth Gems #145

**#16. Tideman**
> "Any action vs. no action comparisons in your analytics will always make your activation metric look predictive, but this is misleading. Users who take any action are already more motivated than those who take none. The real work is finding which specific actions, at what volume and timing, predict retention. Do not mistake correlation with engagement for causation of retention."
**Label:** YES
**Why:** Statistical pitfall + correct approach. Repeatable analytical lesson.

**#17. Tideman**
> "A short, low-friction onboarding can actually hurt activation for complex products. When users breeze through a few questions and land in a complex product with no guidance, they hit a 'now what?' wall and churn fast. For complex apps, a longer onboarding that walks users through setup and delivers early value, even at the cost of completion rate, produces better retention outcomes."
**Label:** YES
**Why:** Counter-intuitive ("longer is better here"). Conditional rule.

**#18. Tideman**
> "Onboarding completion rate is a vanity metric. When an app extended its onboarding to include value-delivering steps before the paywall, completion dropped but retention improved. Optimize your onboarding for felt value, not for speed-to-paywall."
**Label:** YES
**Why:** Reframes a standard metric. Strong directional advice.

**#19. Tideman**
> "When you face both an activation problem and a monetization problem, fix activation first. Monetization naturally follows when users are truly activated. Churn data almost always points back to insufficient usage, which is an activation failure, not a pricing failure."
**Label:** YES
**Why:** Sequencing rule. Diagnostic framework.

**#20. Tideman**
> "Stop chasing one big aha moment. Build a series of mini moments of perceived value instead throughout the funnel. Each small moment (a personalized result, a visual showing the outcome, a first small win) compounds trust and intent."
**Label:** YES
**Why:** Reframes a popular concept (aha moment). Replaces with named alternative.

**#21. Tideman**
> "Use the time-to-first-value vs. time-to-core-value framework. Time to first value = the moment a user thinks 'this is for me' (first session). Time to core value = when users have done the thing repeatedly and feel the real benefit (longer). Separating these helps teams identify exactly where users are dropping off."
**Label:** YES
**Why:** Named framework with definitions. Reusable.

**#22. Tideman**
> "For early-stage apps with limited data, monthly subscriptions are a faster learning tool than annual plans. Monthly renewals force users to make an active decision every 30 days, generating rapid signal on who is truly activated. This behavioral data helps you identify your real activation metrics far faster than waiting for annual renewal data."
**Label:** YES
**Why:** Trade-off principle with reasoning chain.

**#23. Tideman**
> "Revenue is a terrible North Star metric for subscription apps. Optimizing for revenue pushes teams to extract value from users rather than create it, which leads to dark patterns, aggressive paywalls, and short-term gains that destroy long-term retention. Choose activation or engagement-based North Star metrics."
**Label:** YES
**Why:** Strong opinion with mechanism. Identity-shaping for product teams.

**#24. Tideman**
> "Reframe how your team thinks about early churn. 'Day 2 retention' and 'Day 7 retention' are misleading labels — you are not retaining users at that point, you are still activating them. For most apps, true activation takes 7 to 30 days of habit formation. Calling early drop-off a 'retention problem' causes teams to apply the wrong solutions."
**Label:** YES
**Why:** Terminology critique with practical consequence. Diagnostic.

**#25. Tideman**
> "Fixing activation is almost always more impactful than scaling acquisition. If you can convert even 20% more of your existing users into activated users, you reduce CAC, increase LTV, and make acquisition more efficient without spending more on ads. Teams that default to 'we just need more users' are often masking an activation problem with acquisition spend."
**Label:** YES
**Why:** Strategic priority claim. Reusable diagnostic.

### Larissa Morimoto + Adam Hadi — Growth Gems #146

**#26. Hadi (Current)**
> "If a huge out-of-home campaign (billboards, bus stations) doesn't move the needle on downloads, it doesn't mean out-of-home is ineffective. It can mean that it doesn't work if people don't know how your product differentiates and what your brand is, which billboards alone can't establish. Out-of-home is not going to drive direct response. So start on direct response channels, then expand."
**Label:** YES
**Why:** Sequencing principle. Reframes a marketing failure into a sequencing error.

**#27. Morimoto (PhotoRoom)**
> "Worth distinguishing between 'community-native offline' (where events serve users first) vs. 'brand-native offline' (where events serve the brand first). Ask: does this benefit the user and in what way? Rather than: how does this benefit the brand? When the answer to the first question is strong, the brand benefit usually follows."
**Label:** YES
**Why:** Named dichotomy with diagnostic question.

**#28. Morimoto**
> "Comparing brand campaign CPAs directly to paid acquisition CPAs is a creativity killer. The breakthrough comes when you stop measuring brand through a performance lens and instead ask: how do we build love and relationships with potential users? For brand campaigns, track branded search uplift, brand awareness surveys, and qualitative measures."
**Label:** YES
**Why:** Methodology critique + alternative measurement approach.

**#29. Morimoto**
> "Celebrity audience-product fit is more important than celebrity reach or fame. Calm's LeBron James partnership was their most expensive and worst-performing campaign because basketball fans don't care about sleep apps. Always validate audience-to-product relevance before investing in any high-profile partnership."
**Label:** YES
**Why:** Principle with cautionary example. Easy to apply.

**#30. Morimoto**
> "Always factor in UGC or online distribution to maximize offline returns. PhotoRoom rented an LED screen for a photo booth — the result was not primarily foot traffic, but a lot of user-generated content. That single activation reached 15,000 people in person and generated over 4 million impressions once UGC was repurposed online."
**Label:** YES
**Why:** Multiplier principle for offline events. Concrete example illustrates.

### David George — a16z

**#31. George**
> "I think AI is going to end up like electricity or Wi-Fi. The market opportunity for AI is much greater than the software market. The previous cycle of mobile + cloud created ~$10 trillion of new market value. AI will be much larger because the impact on the economy is much larger."
**Label:** YES
**Why:** Strong forecast with analogy. Worldview statement.

**#32. George**
> "Be lenient on early gross margins if input model costs can decline and competition exists at the model layer. As long as there's competition at the model layer, costs will keep going down. AI apps will harness better models and deliver better products over time — they won't need to increase price, but will deliver more value and stickiness while input costs go down."
**Label:** YES
**Why:** Investment heuristic with explicit conditions.

**#33. George**
> "Three ingredients for startups to disrupt incumbents like Salesforce: (1) UI/UX reimagination (proactive agents vs forms), (2) access to new data (unstructured dumped into Databricks-like systems), (3) business model innovation (move beyond seat-based pricing). I think for startups to win, you need all three."
**Label:** YES
**Why:** Named framework with three components.

**#34. George**
> "Consumer stickiness for AI is stronger than expected despite many free alternatives. There have been a tremendous amount of free alternatives thrown at consumers over the last 12 months, and it hasn't had any impact on OpenAI's business. There's way more upside to monetize the base than there is risk of price pressure on today's paying users."
**Label:** YES
**Why:** Contrarian forecast based on observed data.

**#35. Siemiatkowski (Klarna)**
> "The cost of creating software is going down to zero. So far the only thing that's gone down to extremely cheap is software generation. The next thing that's going to hit everyone bad is the switching cost of data. People are going to start solving that problem with AI: how do I get all my data from existing vendor to new vendor with one click? That brings down switching cost, and that's when the real threat to SaaS comes."
**Label:** YES
**Why:** Sequenced prediction with mechanism. High signal.

---

## NO — does not belong in skill (10 examples)

**#36. AppLovin Q1 earnings (factual paragraph)**
> "AppLovin reported its Q1 2026 earnings yesterday: Advertising revenue grew 59.0% to $1.84BN. Net income grew 66.5% to $1.21BN at 65.4% margin. Q2 2026 guidance of $1.915BN to $1.945BN. The stock was volatile in after-hours trading, ending down by roughly 2%."
**Label:** NO
**Why:** Pure facts. Will be stale next quarter. No reusable mental model.

**#37. Meta location fees announcement**
> "Meta will introduce location fees starting July 1st. The fee applies to ads served in a relevant location, not the advertiser's business address. Austria's DST is 5%, France's 3%, the UK's at £500MM threshold, Italy removed thresholds in its 2025 budget."
**Label:** NO
**Why:** News + factual list of percentages. Will be obsolete in 12 months.

**#38. a16z show notes**
> "In this episode, Jen Kha, Head of Investor Relations, and David George, General Partner, discuss how late-stage private markets are evolving as AI reshapes scale, capital intensity, and growth timelines. They explain why AI-driven companies are staying private longer, how infrastructure spending is changing return profiles."
**Label:** NO
**Why:** Metadata / show description. No actual content.

**#39. Klarna intro from podcast notes**
> "Sebastian Siemiatkowski is the co-founder and CEO of Klarna, the global digital bank with over 114 million global active users and 3.4 million transactions per day."
**Label:** NO
**Why:** Bio fact. Belongs in `persona.yaml`, not skill content.

**#40. AppLovin product release news**
> "AppLovin's CEO noted on the earnings call that its eCommerce self-serve ads manager will launch in June. We rolled out something called our interactive page generator earlier in the quarter."
**Label:** NO
**Why:** Product status update. Will be irrelevant in 6 months.

**#41. Snipd weekly summary**
> "🏆 Congrats! You made it into the top 10% most active Snipd users this week. You snipped 12 episodes from 5 different shows."
**Label:** NO
**Why:** Personal usage metric. Zero signal about expertise.

**#42. Podcast sponsor read**
> "Thanks to the sponsors of this week's episode of the Mobile Dev Memo podcast: INCRMNTAL. True attribution measures incrementality, always on. Xsolla. With the Xsolla Web Shop, you can create a direct storefront, cut fees down to as low as 5%, and keep players engaged with bundles, rewards, and analytics."
**Label:** NO
**Why:** Sponsor copy. Not Seufert's view.

**#43. Email subscription metadata**
> "You are receiving this email as subscriber@example.com. Subscription: MDM Pro - Monthly. Next Billing Date: Click here to update your account settings."
**Label:** NO
**Why:** Transactional plumbing. Pure noise.

**#44. Newsletter introduction**
> "Hi, fellow growth practitioner! This week, I'm bringing you insights on Paid UA and creatives. Hannah is amongst the most-featured experts in this newsletter. There are always several gems that make her appearances worth listening to!"
**Label:** NO
**Why:** Editorial preamble. No content yet.

**#45. Specific timestamp + filler**
> "(06:39) For example, if you have one user listening to a piece of content, but another not engaging, it may appear that listening is 'predictive' of activation. (07:46) That said... (09:02) Daphne also mentioned..."
**Label:** NO
**Why:** Timestamps + transitional text only. The thought is elsewhere.

---

## BORDERLINE — judge needs to decide (5 examples)

These are the most important examples for calibrating your threshold. Real-world content is mostly mixed like this.

**#46. Klarna headcount story (Siemiatkowski)**
> "We used to be over 7,000 employees. Now we are just 3,000. Mostly via attrition and AI-driven productivity. I required no extra investment to roll out major product expansions because AI let us do more with fewer people."
**Label:** BORDERLINE → I'd lean YES at threshold ≥0.6
**Why:** The 7000→3000 number is a fact about Klarna specifically. But the framing "no extra investment + more product = AI multiplier" is a reusable principle. Judge should extract the principle, not the number.

**#47. AppLovin growth rate forecast**
> "We've talked about 20% to 30% long-term growth in the games category. We've never had a single quarter that's come close to those growth numbers. We've been way over those rates."
**Label:** BORDERLINE → lean NO
**Why:** Forecast tied to specific company. Not reusable as Seufert's expert view — it's the CEO's claim Seufert is reporting.

**#48. Citing Galbraith (Seufert)**
> "Galbraith argued that in an affluent society, the primary constraint was not one of food production, as with the Malthusian trap, but of the optimal allocation of resources between private endeavors and public institutions. Galbraith's dependence effect argues advertising manufactures preference, not just reveals it."
**Label:** BORDERLINE → lean YES (because Seufert uses this framework as scaffolding for his own argument)
**Why:** Quoting an external thinker. Goes in IF the expert uses this thinker as part of their worldview (Seufert clearly does — Galbraith is core to his thesis). Otherwise NO.

**#49. ChatGPT adoption stat (George)**
> "The time to get to 365 billion searches on ChatGPT was two years. The time for Google to get to 365 billion searches was 11 years. So it's five and a half times faster."
**Label:** BORDERLINE → lean NO (raw stat alone)
**Why:** A specific stat used to illustrate a point. The POINT ("AI demand scales faster because cloud + smartphones eliminate distribution friction") would be YES. The bare comparison without the framing is NO.

**#50. AppLovin customer LTV projection (CEO quote in Seufert article)**
> "We almost never churn customers once they get through the first 30 days on our platform. Right now, we're projecting well over $70,000 a year from every new customer. So if we open up the platform and sign on 100,000 customers in the next year, first year revenue from them would be roughly $7 billion."
**Label:** BORDERLINE → NO if attributed to AppLovin's CEO, YES if Seufert's framing extracts the "30-day-stickiness predicts LTV" principle
**Why:** The number is company-specific. The implicit pattern (30-day retention → LTV anchor) is a principle. Judge should be sensitive to attribution: is this expert's view, or quoted source?

---

## Calibration interpretation guide

Once you've reviewed:
- Count agreements vs flips.
- If >5 NO got flipped to YES → judge prompt too strict (raise sensitivity).
- If >5 YES got flipped to NO → judge prompt too lenient (tighten "what counts as principle").
- BORDERLINE examples don't have "correct" labels — your decisions on those *define* the threshold (~0.7 ≈ "lean towards keeping borderlines").

Next step: feed these 50 to the judge prompt (draft), measure agreement, iterate prompt + threshold until ≥45/50 match.
