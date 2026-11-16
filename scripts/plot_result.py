"""환율 추이, 3개월 평균, Risk 경계선, 권장환율을 한 장의 PNG로 그린다.

계산 엔진(src/fx_core.py)은 표준 라이브러리만 쓰고, 그래프만 matplotlib이 필요하다.
  pip install matplotlib
  python scripts/plot_result.py --csv data/scenario_critical.csv --output docs/charts/chart_critical.png
  python scripts/plot_result.py --all          # 모든 샘플을 docs/charts/에 생성

모든 샘플은 가상 데이터이며 공식 환율이 아니다.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.fx_core import calculate, load_rates, subtract_months  # noqa: E402

RISK_COLOR = {'NORMAL': '#2E9E5B', 'CAUTION': '#D9A400', 'RISK': '#E8742A', 'CRITICAL': '#C8372D'}
SAMPLES = ['sample_rates'] + [f'scenario_{n}' for n in ('normal', 'caution', 'risk', 'critical')]


def _load_matplotlib():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit('오류: matplotlib이 필요합니다. 설치: pip install matplotlib')
    from matplotlib import font_manager
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in ('Malgun Gothic', 'AppleGothic', 'NanumGothic', 'Noto Sans CJK KR'):
        if name in installed:
            plt.rcParams['font.family'] = name
            break
    plt.rcParams['axes.unicode_minus'] = False
    return plt, mdates


def plot(csv_path, output):
    plt, mdates = _load_matplotlib()
    rates = load_rates(csv_path)
    r = calculate(rates)
    base = date.fromisoformat(r['as_of'])
    start = subtract_months(base, 3)
    color = RISK_COLOR[r['risk']]
    avg3 = r['avg3']

    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150)
    days = [x.day for x in rates]
    vals = [x.value for x in rates]

    ax.axvspan(start, base, color='#EEF2F6', zorder=0, label='Rolling 3개월 구간')
    ax.plot(days, vals, color='#1B2A41', linewidth=1.8, label='USD/KRW', zorder=3)
    ax.axhline(avg3, color='#0C7C8A', linewidth=1.8, label=f'3개월 평균 {avg3:,.2f}', zorder=2)
    ax.axhline(r['avg10'], color='#6B7A8F', linewidth=1.3, linestyle=':', label=f"최근 10개 평균 {r['avg10']:,.2f}", zorder=2)
    for pct, name, c in ((-3, 'CAUTION 경계 -3%', RISK_COLOR['CAUTION']),
                         (-7, 'RISK 경계 -7%', RISK_COLOR['RISK']),
                         (-10, 'CRITICAL 경계 -10%', RISK_COLOR['CRITICAL'])):
        ax.axhline(avg3 * (1 + pct / 100), color=c, linewidth=1.1, linestyle='--', alpha=0.9,
                   label=f'{name} ({avg3 * (1 + pct / 100):,.0f})', zorder=2)
    ax.axhline(r['recommended'], color=color, linewidth=2.6, label=f"권장환율 {r['recommended']:,} ({r['risk']})", zorder=4)
    ax.scatter([base], [r['current']], s=70, color=color, edgecolor='white', linewidth=1.5, zorder=5)
    ax.annotate(f"현재 {r['current']:,.2f}\n괴리율 {r['deviation_pct']:+.2f}%",
                xy=(base, r['current']), xytext=(-60, -48), textcoords='offset points',
                arrowprops=dict(arrowstyle='-', color=color, lw=1.2),
                ha='right', fontsize=10, color='#1B2A41',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec=color, lw=1.2), zorder=6)

    ax.set_title(f"USD/KRW 환율 Risk 판정 — {r['risk']}", fontsize=15, fontweight='bold', loc='left', color='#1B2A41', pad=26)
    ax.text(0, 1.015, '가상 데이터 · 공식 환율 아님 · 운영 사용 금지 (SAMPLE_NOT_OFFICIAL)',
            transform=ax.transAxes, fontsize=9, color='#6B7A8F', va='bottom')
    ax.set_ylabel('원/USD')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.grid(axis='y', color='#D5DCE4', linewidth=0.6)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=9)
    fig.tight_layout()

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out, r


def main():
    ap = argparse.ArgumentParser(description='환율 Risk 그래프 PNG 생성')
    ap.add_argument('--csv', default='data/sample_rates.csv')
    ap.add_argument('--output', default='docs/charts/chart.png')
    ap.add_argument('--all', action='store_true', help='모든 샘플 CSV를 docs/charts/에 생성')
    args = ap.parse_args()
    try:
        if args.all:
            for name in SAMPLES:
                out, r = plot(ROOT / 'data' / f'{name}.csv', ROOT / 'docs' / 'charts' / f'chart_{name}.png')
                print(f"{out.relative_to(ROOT)}  {r['risk']}  recommended={r['recommended']}")
        else:
            out, r = plot(args.csv, args.output)
            print(f"{out}  {r['risk']}  recommended={r['recommended']}")
    except (OSError, ValueError) as e:
        raise SystemExit(f'오류: {e}')


if __name__ == '__main__':
    main()
