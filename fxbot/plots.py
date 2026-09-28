"""Static charts (PNG) for the research report. One y-axis per panel, thin marks."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import numpy as np
import pandas as pd

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]     # categorical slots 1-3, fixed order
LIMIT = "#52514e"                              # reference lines use secondary ink
DIVERGING = LinearSegmentedColormap.from_list("rb", ["#e34948", "#f0efec", "#2a78d6"])


def _t(text):
    """Escape '$' so matplotlib does not read dollar amounts as math."""
    return str(text).replace("$", r"\$")


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.title.set_color(TEXT)


def _fig(*args, **kw):
    fig, axes = plt.subplots(*args, **kw)
    fig.patch.set_facecolor(SURFACE)
    return fig, axes


def equity_chart(curves, account, path, title):
    """curves: ordered dict name -> equity DataFrame. First curve gets the drawdown panel."""
    fig, (ax1, ax2) = _fig(2, 1, figsize=(12, 7.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.4]})
    floor = account.initial * (1 - account.max_loss_pct)
    target = account.initial * (1 + account.target_pct)
    for k, (name, eq) in enumerate(curves.items()):
        d = pd.to_datetime(eq["date"])
        ax1.plot(d, eq["equity_close"], color=SERIES[k], linewidth=2 if k == 0 else 1.4, label=_t(name))
        ax1.annotate(_t(f"{name}  ${eq['equity_close'].iloc[-1]:,.0f}"), (d.iloc[-1], eq["equity_close"].iloc[-1]),
                     xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=TEXT)
    for y, lab in ((floor, "FTMO max loss $9,000"), (account.initial, "start $10,000"),
                   (target, "phase-1 target $11,000")):
        ax1.axhline(y, color=LIMIT, linewidth=0.9, linestyle=(0, (4, 3)))
        ax1.annotate(_t(lab), (0.005, y), xycoords=("axes fraction", "data"), xytext=(0, 3),
                     textcoords="offset points", fontsize=8, color=TEXT_2)
    ax1.set_ylabel("Equity ($, marked to market daily)", color=TEXT_2)
    ax1.set_title(_t(title), loc="left", fontsize=12)
    ax1.legend(loc="upper center", frameon=False, fontsize=9)

    # FTMO's max loss is static: measured from the starting balance, not the peak
    name0, eq0 = next(iter(curves.items()))
    d0 = pd.to_datetime(eq0["date"])
    dd = (eq0["equity_low"] - account.initial) / account.initial * 100
    ax2.fill_between(d0, dd.clip(upper=0), 0, color=SERIES[0], alpha=0.25, linewidth=0)
    ax2.plot(d0, dd, color=SERIES[0], linewidth=1)
    for y, lab in ((-10, "FTMO 10% limit"), (-8, "8% safety buffer")):
        ax2.axhline(y, color=LIMIT, linewidth=0.9, linestyle=(0, (4, 3)))
        ax2.annotate(lab, (0.005, y), xycoords=("axes fraction", "data"), xytext=(0, 3),
                     textcoords="offset points", fontsize=8, color=TEXT_2)
    ax2.set_ylim(min(-11, dd.min() - 1), max(1, dd.max() + 1))
    ax2.axhline(0, color=AXIS, linewidth=1)
    ax2.set_ylabel(_t(f"Worst equity vs $10k start, %\n({name0.split(',')[0]})"), color=TEXT_2)
    for ax in (ax1, ax2):
        _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def drift_chart(drift, chosen, path, title):
    """Small multiples: one panel per parameter, y = net R over the test period."""
    params = list(dict.fromkeys(drift["param"]))
    fig, axes = _fig(1, len(params), figsize=(3.1 * len(params), 3.6), sharey=True)
    for ax, name in zip(np.atleast_1d(axes), params):
        sub = drift[drift["param"] == name]
        xs = [str(v) for v in sub["value"]]
        ys = sub["net_r"].to_numpy()
        if name in ("trend", "entry"):
            ax.bar(xs, ys, color=SERIES[0], width=0.6)
        else:
            ax.plot(xs, ys, color=SERIES[0], linewidth=2, marker="o", markersize=5)
        sel = xs.index(str(chosen[name])) if str(chosen[name]) in xs else None
        if sel is not None:
            ax.plot([xs[sel]], [ys[sel]], marker="o", markersize=9, markerfacecolor="none",
                    markeredgecolor=TEXT, markeredgewidth=1.5, linestyle="none")
        ax.axhline(0, color=AXIS, linewidth=1)
        ax.set_title(name, fontsize=10, loc="left")
        ax.tick_params(axis="x", rotation=30)
        _style(ax)
    np.atleast_1d(axes)[0].set_ylabel("Net result (R)", color=TEXT_2)
    fig.suptitle(_t(title), x=0.01, ha="left", fontsize=11, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def heatmap(table, path, title, xlabel, ylabel):
    fig, ax = _fig(figsize=(6.2, 4.4))
    vals = table.to_numpy(float)
    lim = max(abs(np.nanmin(vals)), abs(np.nanmax(vals)), 1e-9)
    im = ax.imshow(vals, cmap=DIVERGING, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    ax.set_xticks(range(table.shape[1]), [str(c) for c in table.columns])
    ax.set_yticks(range(table.shape[0]), [str(r) for r in table.index])
    for (r, c), v in np.ndenumerate(vals):
        ax.text(c, r, f"{v:+.1f}", ha="center", va="center", fontsize=9, color=TEXT)
    ax.set_xlabel(xlabel, color=TEXT_2)
    ax.set_ylabel(ylabel, color=TEXT_2)
    ax.set_title(_t(title), loc="left", fontsize=10, color=TEXT)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label("Net R", color=TEXT_2)
    cb.ax.tick_params(colors=TEXT_2, labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
