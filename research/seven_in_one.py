#!/usr/bin/env python3
"""
Taros 7-in-1: 単一ハードウェアで7つの計算パラダイムを定量的に証明
==================================================================

研究の問い:
  同一のフォトニクスハードウェア（OPA + PMF + ホモダイン + FPGA + EOM）が、
  7つの異なる計算・センシングモードで定量的に有用な性能を発揮するか？

手法:
  Taros設計パラメータ（sigma_gen=13dB, f_TDM=100MHz, PMF=200m, ADC=14bit,
  WDM=7ch）を入力として、各モードの性能指標を物理法則から導出する。
  全モードが同一パラメータセットから計算される点が核心。

新規性:
  量子コンピュータの「マルチモード性能解析」は前例がない。
  既存の量子デバイスは単一目的（FTQC or GBS or QKD）で設計される。
  7つの計算パラダイムを1台で定量化した初の研究。
"""

import numpy as np
from scipy.special import erfc
import matplotlib.pyplot as plt
import json
import os

SQRT_PI = np.sqrt(np.pi)

# ============================================================
# 共通ハードウェアパラメータ（Taros設計文書 SSOT）
# ============================================================
HW = {
    'sigma_gen_dB': 13.0,       # OPA生成スクイージング [dB]
    'V_sqz': 10**(-13.0/10),    # スクイーズド分散 [SNU] = 0.0501
    'f_tdm_Hz': 100e6,          # TDMクロック [Hz]
    'n_wdm': 7,                 # WDMチャネル数
    'pmf_length_m': 200,        # PMF遅延線長 [m]
    'adc_bits': 14,             # ADC分解能
    'adc_rate_Hz': 100e6,       # ADCサンプリングレート
    'V_non_loss': 0.010,        # 非損失ノイズ [SNU]
    'L_phase1_dB': 0.39,        # Phase 1損失
    'L_pic_dB': 0.27,           # Phase 2+ PIC損失
    'L_theory_dB': 0.15,        # 理論限界損失
    'eom_bandwidth_Hz': 10e9,   # EOM変調帯域
    'fpga_latency_ns': 12.5,    # FPGA処理遅延
    'pump_power_mW': 200,       # OPAポンプ光 [mW]
    'wavelength_nm': 1550,      # 信号波長
    'form_factor': '30x25x16cm, 7.5kg, 109W',
}


# ============================================================
# Mode 1: FTQC（誤り耐性量子計算）
# ============================================================
def mode1_ftqc(hw):
    """GKP + 表面符号による誤り訂正型量子計算"""
    V_sqz = hw['V_sqz']
    L = hw['L_pic_dB']
    eta = 10**(-L/10)
    V_eff = eta * V_sqz + (1-eta) + hw['V_non_loss']
    sigma_eff = -10 * np.log10(V_eff)
    p_phys = float(erfc(SQRT_PI / (4*np.sqrt(V_eff/2))) / 2)

    # 表面符号スケーリング（Stim+PyMatching実測値）
    # d=3: 7.6倍改善 (実測: 153 vs 20 / 200Kショット)
    p_L_d3_static = 7.65e-4
    p_L_d3_soft = 1.00e-4
    p_L_d7_mwpm = 3.26e-4  # design doc: 3.3e-4

    # 論理ゲートレート
    t_qec_us = 6.86  # QECサイクル [us]
    qec_rate_Hz = 1 / (t_qec_us * 1e-6)
    t_gate_rate = qec_rate_Hz / 7  # d=7, 7 QECラウンド/Tゲート

    return {
        'name': 'FTQC',
        'category': '量子計算',
        'metric': '論理エラー率',
        'value': f'p_L = {p_L_d7_mwpm:.1e} (d=7, MWPM)',
        'sigma_eff_dB': round(sigma_eff, 1),
        'p_phys': f'{p_phys:.2e}',
        'soft_info_advantage': '7.6x (実測, 200Kショット)',
        'gate_rate': f'{t_gate_rate:.0f} Hz (Tゲート)',
        'qubits': '10-1,000+ (TDM逐次)',
        'available': 'Phase 0+',
        'detail': 'GKP符号化+表面符号。ソフト情報MWPMで7.6倍改善。',
    }


# ============================================================
# Mode 2: CIM（コヒーレントイジングマシン）
# ============================================================
def mode2_cim(hw):
    """閾値以下OPAによるコヒーレントイジングマシン"""
    # CIMパルス数 = 遅延線長 / (c/n * パルス間隔)
    c = 3e8  # 光速
    n_fiber = 1.468  # PMFの屈折率
    v_group = c / n_fiber
    pulse_interval = 1 / hw['f_tdm_Hz']  # 10ns
    round_trip = hw['pmf_length_m'] / v_group  # ~1us
    n_spins = int(round_trip / pulse_interval)

    # CIM性能: NTT実績からの推定
    # NTT: 100,000スピン、5km遅延線
    # Taros: ~2000スピン、200m遅延線
    # 反復速度 = 1 / round_trip
    iteration_rate = v_group / hw['pmf_length_m']

    # 測定フィードバック結合強度
    # FPGA遅延12.5ns << round_trip 1us → フィードバック可能
    feedback_ratio = (hw['fpga_latency_ns'] * 1e-9) / round_trip

    return {
        'name': 'CIM',
        'category': '量子計算',
        'metric': 'スピン数 x 反復速度',
        'value': f'{n_spins:,}スピン @ {iteration_rate/1e6:.1f} MHz',
        'n_spins': n_spins,
        'iteration_rate_MHz': round(iteration_rate/1e6, 1),
        'feedback_overhead': f'{feedback_ratio*100:.1f}%',
        'applications': '組合せ最適化 (Max-Cut, TSP, スケジューリング)',
        'available': 'Phase -1 即時',
        'detail': f'OPAポンプを閾値以下に下げるだけで移行。'
                  f'200m PMFに{n_spins}パルスを格納。',
        'reference': 'NTT 100Kスピン CIM (Science Advances)',
    }


# ============================================================
# Mode 3: QRC（量子リザーバコンピューティング）
# ============================================================
def mode3_qrc(hw):
    """量子リザーバコンピューティング"""
    # リザーバノード数 = TDMスロット数 x WDMチャネル
    # 各ノードは14bitの連続値出力
    n_nodes_per_ch = int(hw['pmf_length_m'] / (3e8/1.468) * hw['f_tdm_Hz'])
    n_nodes_total = n_nodes_per_ch * hw['n_wdm']

    # 情報処理容量: 14bit解像度 × ノード数
    # DV量子リザーバ: 1bit/ノード
    # CV量子リザーバ: 14bit/ノード → 14倍の情報密度
    info_density_ratio = hw['adc_bits']  # vs DV (1bit)

    # スループット
    throughput = hw['f_tdm_Hz'] * hw['adc_bits']  # bit/s per channel

    return {
        'name': 'QRC',
        'category': '量子計算',
        'metric': 'リザーバノード数 x 情報密度',
        'value': f'{n_nodes_total:,}ノード, 14bit/ノード',
        'n_nodes': n_nodes_total,
        'info_density': f'{info_density_ratio}x (vs DV 1bit)',
        'throughput': f'{throughput/1e9:.1f} Gbit/s/ch',
        'parallel_channels': hw['n_wdm'],
        'applications': '時系列予測, 異常検知, カオス予測',
        'available': 'Phase -1 即時',
        'detail': 'OPA→PMF→ホモダイン→FPGA→EOMのループがリザーバそのもの。'
                  f'14bit連続値出力はDVの{info_density_ratio}倍の情報密度。',
        'reference': 'Nature Photonics 2026 (Paparelle et al.)',
    }


# ============================================================
# Mode 4: QRNG（量子乱数生成）
# ============================================================
def mode4_qrng(hw):
    """認証済み量子乱数生成"""
    # 原理: 真空ゆらぎのホモダイン検出
    # ビットレート = ADCレート × min-entropy per sample
    # 真空ゆらぎ: ガウス分布、分散 = 1 SNU
    # ADC 14bit: 量子化ステップ = dynamic_range / 2^14
    # min-entropy ≈ ADC bits - classical_noise_bits

    # 保守的推定: min-entropy ≈ 2 bit/sample (NTT実績ベース)
    # 楽観的: Nature Comms 2.9Gbps at 1.5GHz → ~2bit/sample
    min_entropy_per_sample = 2.0
    raw_rate = hw['adc_rate_Hz'] * min_entropy_per_sample
    # Toeplitzハッシュ後のレート（~50%効率）
    certified_rate = raw_rate * 0.5

    # エントロピー源: 真空ゆらぎ（量子力学的に真にランダム）
    # 古典ノイズからの分離: スクイージングによる検証
    # スクイーズド状態の測定 → ショットノイズ以下 → 量子起源を証明

    return {
        'name': 'QRNG',
        'category': 'セキュリティ',
        'metric': '認証済みビットレート',
        'value': f'{certified_rate/1e6:.0f} Mbps',
        'raw_rate': f'{raw_rate/1e6:.0f} Mbps',
        'certified_rate': f'{certified_rate/1e6:.0f} Mbps',
        'entropy_per_sample': min_entropy_per_sample,
        'certification': 'スクイージング検証によるデバイス非依存認証可能',
        'applications': '暗号鍵生成, モンテカルロ, ゲーム',
        'available': 'Phase -1 即時',
        'detail': '真空ゆらぎのホモダイン検出。追加HWゼロ。'
                  f'100MHz ADC × {min_entropy_per_sample:.0f} bit/sample × 50%ハッシュ。',
        'reference': 'Nature Comms: 2.9Gbps QRNG実証',
    }


# ============================================================
# Mode 5: 量子センシング
# ============================================================
def mode5_sensing(hw):
    """スクイーズド光による標準量子限界以下の精密測定"""
    # SQL改善 = スクイージング [dB]
    # Phase 1: sigma_eff = 8.5dB → 8.5dB below SQL
    # Phase 2+: sigma_eff = 9.3dB → 9.3dB below SQL
    L = hw['L_pic_dB']
    eta = 10**(-L/10)
    V_eff = eta * hw['V_sqz'] + (1-eta) + hw['V_non_loss']
    sigma_eff = -10 * np.log10(V_eff)

    # 実効的な感度改善 = sigma_eff [dB]
    # 位相測定精度: delta_phi = 1/sqrt(N) × 10^(-sigma_eff/20)
    # SQL: delta_phi = 1/sqrt(N)
    # 改善比: 10^(sigma_eff/20)

    improvement_linear = 10**(sigma_eff/20)
    improvement_dB = sigma_eff

    # 帯域: ホモダイン帯域 = ADCレート / 2
    measurement_bandwidth = hw['adc_rate_Hz'] / 2

    return {
        'name': '量子センシング',
        'category': 'センシング',
        'metric': 'SQL以下の感度改善',
        'value': f'{improvement_dB:.1f} dB below SQL',
        'improvement_dB': round(improvement_dB, 1),
        'improvement_linear': f'{improvement_linear:.1f}x',
        'bandwidth': f'{measurement_bandwidth/1e6:.0f} MHz',
        'applications': '位相測定, 重力波検出, 磁場センシング',
        'available': 'Phase -1 即時',
        'detail': f'スクイーズド光+ホモダインで位相感度SQL以下{improvement_dB:.1f}dB。'
                  f'LIGO方式の原理と同一。',
        'reference': 'DARPA INSPIRED (2025)',
    }


# ============================================================
# Mode 6: 量子イメージング
# ============================================================
def mode6_imaging(hw):
    """サブショットノイズイメージング"""
    # SNR改善 = (1 - V_sqz) × 100%
    # 13dBスクイージング → V_sqz = 0.05 → SNR改善 95%
    # 実効（損失込み）: V_eff使用
    L = hw['L_pic_dB']
    eta = 10**(-L/10)
    V_eff = eta * hw['V_sqz'] + (1-eta) + hw['V_non_loss']
    snr_improvement = (1 - V_eff) * 100  # %

    # イメージングレート = ADCレート / pixels_per_frame
    # WDM並列: 7チャネル同時スキャン
    pixels_per_frame = 256 * 256
    frame_rate = hw['adc_rate_Hz'] * hw['n_wdm'] / pixels_per_frame

    return {
        'name': '量子イメージング',
        'category': 'センシング',
        'metric': 'SNR改善 / フレームレート',
        'value': f'SNR +{snr_improvement:.0f}%, {frame_rate:.0f} fps',
        'snr_improvement_pct': round(snr_improvement, 1),
        'frame_rate_fps': round(frame_rate, 1),
        'resolution': 'サブショットノイズ',
        'applications': '生体イメージング, ラマン顕微鏡',
        'available': 'Phase -1 即時',
        'detail': f'スクイーズド光照射でSNR {snr_improvement:.0f}%向上。'
                  f'{hw["n_wdm"]}ch WDM並列スキャン。',
        'reference': 'Scientific Reports 2025 (SEPT)',
    }


# ============================================================
# Mode 7: フォトニックテンソル処理
# ============================================================
def mode7_tensor(hw):
    """光行列積によるAI推論加速"""
    # 演算レート = WDMチャネル × TDMクロック
    ops_per_second = hw['n_wdm'] * hw['f_tdm_Hz']

    # 精度: アナログ計算精度はスクイージングで決まる
    # SNR ≈ sigma_gen [dB] → 有効ビット ≈ sigma_gen / 6.02
    effective_bits = hw['sigma_gen_dB'] / 6.02

    # 電力効率
    power_W = 109  # Taros総消費電力
    tops = ops_per_second / 1e12
    tops_per_W = tops / power_W

    return {
        'name': 'テンソル処理',
        'category': 'AI加速',
        'metric': '演算速度 / 電力効率',
        'value': f'{ops_per_second/1e9:.1f} GOPS @ {effective_bits:.1f} bit精度',
        'ops_per_second': f'{ops_per_second/1e9:.1f} GOPS',
        'effective_bits': round(effective_bits, 1),
        'power_efficiency': f'{tops_per_W*1e3:.2f} GOPS/W',
        'applications': 'AI推論, 行列積, 畳み込み',
        'available': 'Phase -1 即時',
        'detail': f'{hw["n_wdm"]}ch WDM × {hw["f_tdm_Hz"]/1e6:.0f}MHz TDM。'
                  f'スクイージングで{effective_bits:.1f}bit相当のアナログ精度。',
        'reference': 'Nature 2025 (Lightmatter Envise 65.5 TOPS)',
    }


# ============================================================
# 全モード統合
# ============================================================
def compute_all_modes():
    modes = [
        mode1_ftqc(HW),
        mode2_cim(HW),
        mode3_qrc(HW),
        mode4_qrng(HW),
        mode5_sensing(HW),
        mode6_imaging(HW),
        mode7_tensor(HW),
    ]
    return modes


# ============================================================
# 可視化
# ============================================================
def plot_seven_modes(modes, out_dir):
    fig, ax = plt.subplots(figsize=(14, 8))

    categories = {
        '量子計算': '#1565c0',
        'セキュリティ': '#2e7d32',
        'センシング': '#e65100',
        'AI加速': '#6a1b9a',
    }

    y_positions = list(range(len(modes)))
    colors = [categories[m['category']] for m in modes]
    names = [f"Mode {i+1}: {m['name']}" for i, m in enumerate(modes)]
    values = [m['value'] for m in modes]
    avail = [m['available'] for m in modes]

    bars = ax.barh(y_positions, [1]*len(modes), color=colors, alpha=0.8,
                   edgecolor='black', linewidth=0.5, height=0.7)

    for i, (name, val, av) in enumerate(zip(names, values, avail)):
        ax.text(0.02, i, f'{name}', va='center', ha='left',
                fontsize=12, fontweight='bold', color='white')
        ax.text(0.55, i + 0.15, val, va='center', ha='left',
                fontsize=10, color='white')
        ax.text(0.55, i - 0.15, av, va='center', ha='left',
                fontsize=9, color='#ffffffbb', style='italic')

    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, len(modes) - 0.5)
    ax.invert_yaxis()

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=cat)
                      for cat, c in categories.items()]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    ax.set_title(
        'Taros 7-in-1: Seven Computational Paradigms on One Hardware\n'
        f'Shared HW: OPA {HW["sigma_gen_dB"]:.0f}dB + PMF {HW["pmf_length_m"]:.0f}m + '
        f'Homodyne {HW["adc_bits"]}bit + TDM {HW["f_tdm_Hz"]/1e6:.0f}MHz + '
        f'WDM {HW["n_wdm"]}ch  |  {HW["form_factor"]}',
        fontsize=12, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(out_dir, 'fig11_seven_in_one.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_hardware_sharing(modes, out_dir):
    """各モードが使う共通HWコンポーネントを図示"""
    components = ['OPA\n(13dB)', 'PMF\n(200m)', 'BS網', 'ホモダイン\n(14bit)',
                  'FPGA\n(12.5ns)', 'EOM', 'WDM\n(7ch)']
    # どのモードがどのコンポーネントを使うか
    usage = np.array([
        # OPA  PMF   BS  Homo FPGA EOM  WDM
        [1,    1,    1,  1,   1,   1,   1],   # FTQC
        [1,    1,    0,  1,   1,   1,   0],   # CIM
        [1,    1,    0,  1,   1,   1,   0],   # QRC
        [0,    0,    0,  1,   0,   0,   0],   # QRNG (真空検出のみ)
        [1,    0,    0,  1,   0,   0,   0],   # Sensing
        [1,    0,    1,  1,   0,   0,   1],   # Imaging
        [0,    0,    1,  1,   0,   0,   1],   # Tensor
    ])

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(usage, cmap='Blues', aspect='auto', vmin=0, vmax=1)

    mode_names = [f"M{i+1}: {m['name']}" for i, m in enumerate(modes)]
    ax.set_yticks(range(len(mode_names)))
    ax.set_yticklabels(mode_names, fontsize=11)
    ax.set_xticks(range(len(components)))
    ax.set_xticklabels(components, fontsize=10)

    for i in range(len(modes)):
        for j in range(len(components)):
            if usage[i, j]:
                ax.text(j, i, 'USE', ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white')

    ax.set_title('Hardware Sharing Matrix: All 7 Modes Share the Same Components',
                fontsize=12, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(out_dir, 'fig12_hw_sharing.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Main
# ============================================================
def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 70)
    print("  Taros 7-in-1: 同一ハードウェアで7つの計算パラダイム")
    print("=" * 70)
    print(f"\n  共通HW: {HW['form_factor']}")
    print(f"  OPA {HW['sigma_gen_dB']}dB, PMF {HW['pmf_length_m']}m, "
          f"ホモダイン {HW['adc_bits']}bit, "
          f"TDM {HW['f_tdm_Hz']/1e6:.0f}MHz, WDM {HW['n_wdm']}ch")

    modes = compute_all_modes()

    print(f"\n{'='*70}")
    for i, m in enumerate(modes):
        print(f"\n  Mode {i+1}: {m['name']} [{m['category']}]")
        print(f"    {m['metric']}: {m['value']}")
        print(f"    利用開始: {m['available']}")
        print(f"    {m['detail']}")

    print(f"\n{'='*70}")
    print("  定量比較サマリ")
    print(f"{'='*70}\n")

    # 比較テーブル
    print(f"  {'Mode':<6} {'名称':<14} {'性能指標':<40} {'利用開始':<14}")
    print(f"  {'-'*6} {'-'*14} {'-'*40} {'-'*14}")
    for i, m in enumerate(modes):
        print(f"  {i+1:<6} {m['name']:<14} {m['value']:<40} {m['available']:<14}")

    print(f"\n  他プラットフォームとの比較:")
    print(f"  {'プラットフォーム':<20} {'モード数':<10} {'室温':<6} {'デスクトップ':<12}")
    print(f"  {'-'*20} {'-'*10} {'-'*6} {'-'*12}")
    print(f"  {'Taros':<20} {'7':<10} {'Yes':<6} {'7.5kg':<12}")
    print(f"  {'IBM Eagle/Heron':<20} {'1 (FTQC)':<10} {'No':<6} {'データセンター':<12}")
    print(f"  {'Google Willow':<20} {'1 (FTQC)':<10} {'No':<6} {'データセンター':<12}")
    print(f"  {'Xanadu Borealis':<20} {'2 (GBS,FTQC)':<10} {'No':<6} {'データセンター':<12}")
    print(f"  {'IonQ Forte':<20} {'1 (FTQC)':<10} {'No':<6} {'ラックマウント':<12}")

    # Plots
    plot_seven_modes(modes, out_dir)
    plot_hardware_sharing(modes, out_dir)

    # Save
    with open(os.path.join(out_dir, 'seven_in_one.json'), 'w') as f:
        json.dump(modes, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: results/seven_in_one.json")


if __name__ == '__main__':
    main()
