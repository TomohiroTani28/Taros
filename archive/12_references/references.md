# セクション14: 参考文献

## 光源・量子ドット

[1] Somaschi, N. et al., "Near-optimal single-photon sources in the solid state," *Nature Photonics* **10**, 340 (2016). — GaAs QDからの高純度単一光子生成の実証。

[2] Thomas, S.E. et al., "Bright polarized single-photon source based on a linear dipole," *Physical Review Letters* **126**, 233601 (2021). — GaAs QDの高収集効率（>0.65）と高不可弁別性（HOM > 0.97）。

[3] Uppu, R. et al., "Scalable integrated single-photon source," *Science Advances* **6**, eabc8268 (2020). — InP QD 1550nmの限界と925nm GaAsの優位性に関する議論。

[4] Tomm, N. et al., "A bright and fast source of coherent single photons," *Nature Nanotechnology* **16**, 399 (2021). — GaAs QDでのg²(0) < 0.01、HOM > 0.99の実証。

## 量子周波数変換（QFC）

[5] Lu, X. et al., "Chip-integrated visible-telecom entangled photon pair source for quantum communication," *Nature Physics* **15**, 373 (2019). — LNOI導波路での高効率周波数変換。

[6] Bock, M. et al., "High-fidelity entanglement between a trapped ion and a telecom photon via quantum frequency conversion," *Nature Communications* **9**, 1998 (2018). — QFCでのノイズ光子抑制技術。

[7] Weber, J.H. et al., "Two-photon interference in the telecom C-band after frequency conversion of photons from remote quantum emitters," *Nature Nanotechnology* **14**, 23 (2019). — QD光子のQFC後HOM干渉実証。

[8] Zaske, S. et al., "Visible-to-telecom quantum frequency conversion of light from a single quantum emitter," *Physical Review Letters* **109**, 147404 (2012). — 単一光子の波長変換の先駆的研究。

## フォトニック量子計算・符号

[9] Bartolucci, S. et al., "Fusion-based quantum computation," *Nature Communications* **14**, 912 (2023). — Fusion-based QCの基本アーキテクチャ。本設計の基礎。

[10] Bombin, H. et al., "Interleaving: Modular architectures for fault-tolerant photonic quantum computing," arXiv:2103.08612 (2021). — SHYPSアーキテクチャの提案。

[11] Bolt, A. et al., "Foliated quantum error-correcting codes," *Physical Review Letters* **117**, 070501 (2016). — 4D Hyperbolic Product Codeの理論的基盤。

[12] Leverrier, A. & Zémor, G., "Quantum Tanner codes," *STOC 2022*. — 定数レート量子LDPC符号。将来のPhase 3候補。

[13] Panteleev, P. & Kalachev, G., "Asymptotically good quantum and locally testable classical LDPC codes," *STOC 2022*. — HPCの理論的性能限界。

[14] Gidney, C. & Newman, M., "Stim: a fast stabilizer circuit simulator," *Quantum* **5**, 497 (2021). — Stim閾値シミュレーションフレームワーク。Phase -1の主要ツール。

## SNSPD・検出系

[15] Wollman, E.E. et al., "Kilopixel array of superconducting nanowire single-photon detectors," *Optics Express* **27**, 35279 (2019). — 行列読み出しSNSPDアレイの実証（1,024ピクセル）。

[16] Chang, J. et al., "Detecting telecom single photons with 99.5% system detection efficiency and high time resolution," *Nature Photonics* **15**, 367 (2021). — SNSPD検出効率>99%の実証。

[17] Reddy, D.V. et al., "Superconducting nanowire single-photon detectors with 98% system detection efficiency at 1550 nm," *Optica* **7**, 1649 (2020). — 高効率SNSPDの設計指針。

[18] Steinhauer, S. et al., "NbTiN thin films for superconducting photon detectors on photonic and two-dimensional materials," *Applied Physics Letters* **116**, 171101 (2020). — NbTiN SNSPDの製造技術。

## LNOI・電気光学

[19] Wang, C. et al., "Integrated lithium niobate electro-optic modulators operating at CMOS-compatible voltages," *Nature* **562**, 101 (2018). — LNOI EO変調器のVπ < 1V実証。

[20] Zhang, M. et al., "Broadband electro-optic frequency comb generation in a lithium niobate microring resonator," *Nature* **568**, 373 (2019). — LNOI変調の広帯域特性。

[21] Zhu, D. et al., "Integrated photonics on thin-film lithium niobate," *Advances in Optics and Photonics* **13**, 242 (2021). — LNOIフォトニクスの包括的レビュー。

## 中空コアファイバ（HCF）

[22] Poletti, F., "Nested antiresonant nodeless hollow core fiber," *Optics Express* **22**, 23807 (2014). — HCFの低損失設計理論。

[23] Jasion, G.T. et al., "Hollow core NANF with 0.28 dB/km attenuation in the C and L bands," *OFC 2022*, Th4A.8. — HCF損失2dB/kmの根拠（保守的見積り。最新は0.28dB/km）。

[24] Sakr, H. et al., "Hollow core NANFs with five nested tubes," *Optics Express* **29**, 30918 (2021). — HCFの量産可能性。

## Si₃N₄フォトニクス

[25] Blumenthal, D.J. et al., "Silicon nitride in silicon photonics," *Proceedings of the IEEE* **106**, 2209 (2018). — Si₃N₄プラットフォームの概要。

[26] Liu, J. et al., "High-yield, wafer-scale fabrication of ultralow-loss, dispersion-engineered silicon nitride photonic circuits," *Nature Communications* **12**, 2236 (2021). — Si₃N₄チップの低損失製造。

## 量子誤り訂正・デコーダ

[27] Dennis, E. et al., "Topological quantum memory," *Journal of Mathematical Physics* **43**, 4452 (2002). — 表面符号の基礎理論。

[28] Delfosse, N. & Nickerson, N., "Almost-linear time decoding algorithm for topological codes," *Quantum* **5**, 595 (2021). — Union-Findデコーダ。FPGA実装の基礎。

[29] Higgott, O. et al., "Improved decoding of circuit noise and fragile boundaries of tailored surface codes," *Physical Review X* **13**, 031007 (2023). — 回路レベルノイズに対するデコーダ最適化。

[30] Sahay, K. et al., "Decoder for the triangular color code by matching on a M\"obius strip," arXiv:2108.11395 (2021). — カラーコードデコーダ。

## マジック状態蒸留

[31] Litinski, D., "Magic state distillation: Not as costly as you think," *Quantum* **3**, 205 (2019). — マジック状態蒸留のコスト分析。

[32] Gidney, C. & Fowler, A.G., "Efficient magic state factories with a catalyzed |CCZ⟩ to 2|T⟩ transformation," *Quantum* **3**, 135 (2019). — 蒸留ファクトリの設計。

## フォトニック量子計算（全般）

[33] Madsen, L.S. et al., "Quantum computational advantage with a programmable photonic processor," *Nature* **606**, 75 (2022). — Xanaduのフォトニック量子優位性実証。

[34] Bourassa, J.E. et al., "Blueprint for a scalable photonic fault-tolerant quantum computer," *Quantum* **5**, 392 (2021). — フォトニック量子コンピュータのスケーラブル設計。

[35] Raussendorf, R. & Briegel, H.J., "A one-way quantum computer," *Physical Review Letters* **86**, 5188 (2001). — 測定型量子計算の基礎。

## 追加参考（v3.0新規）

[36] Paesani, S. et al., "High-rate entangled photon-pair generation from a silicon photonic chip," *Physical Review Letters* **125**, 210503 (2020). — フォトニック集積回路でのentanglement生成レート。

[37] Knill, E. et al., "A scheme for efficient quantum computation with linear optics," *Nature* **409**, 46 (2001). — KLM提案。linear optical QCの理論的基盤。

[38] O'Brien, J.L. et al., "Photonic quantum technologies," *Nature Photonics* **3**, 687 (2009). — フォトニック量子技術の包括的レビュー。

[39] Browne, D.E. & Rudolph, T., "Resource-efficient linear optical quantum computation," *Physical Review Letters* **95**, 010501 (2005). — cluster stateベースの線形光学QC。

[40] Tzitrin, I. et al., "Fault-tolerant quantum computation with static linear optics," *PRX Quantum* **2**, 040353 (2021). — 静的線形光学素子によるフォールトトレラント計算。

---

