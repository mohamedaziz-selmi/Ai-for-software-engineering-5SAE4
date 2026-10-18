"""Static PNG figures for the written reports (the dashboard renders its own charts from JSON)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .config import FIGURES_DIR  # noqa: E402

INK = "#24212b"
ACCENT = "#6f5fb0"
SECOND = "#c0793a"


def _save(fig, name):
	FIGURES_DIR.mkdir(parents=True, exist_ok=True)
	path = FIGURES_DIR / name
	fig.tight_layout()
	fig.savefig(path, dpi=120)
	plt.close(fig)
	return path.relative_to(FIGURES_DIR.parent.parent).as_posix()


def line(name, x, series, title, ylabel):
	fig, ax = plt.subplots(figsize=(10, 3.6))
	for label, values, color in series:
		ax.plot(x, values, label=label, color=color, linewidth=1.1)
	ax.set_title(title, color=INK)
	ax.set_ylabel(ylabel)
	ax.grid(alpha=0.25)
	if len(series) > 1:
		ax.legend(frameon=False)
	return _save(fig, name)


def hist(name, values, title, xlabel, bins=40, log=False):
	fig, ax = plt.subplots(figsize=(6, 3.6))
	values = np.asarray(values, dtype=float)
	ax.hist(np.log1p(np.clip(values, 0, None)) if log else values, bins=bins, color=ACCENT, alpha=0.85)
	ax.set_title(title, color=INK)
	ax.set_xlabel(f"log1p({xlabel})" if log else xlabel)
	ax.set_ylabel("count")
	ax.grid(alpha=0.25)
	return _save(fig, name)


def bars(name, labels, values, title, ylabel):
	fig, ax = plt.subplots(figsize=(7, 3.6))
	ax.bar(labels, values, color=ACCENT)
	ax.set_title(title, color=INK)
	ax.set_ylabel(ylabel)
	ax.tick_params(axis="x", rotation=45)
	ax.grid(alpha=0.25, axis="y")
	return _save(fig, name)


def elbow(name, ks, inertia, silhouette):
	fig, left = plt.subplots(figsize=(7, 3.6))
	left.plot(ks, inertia, marker="o", color=ACCENT, label="inertia")
	left.set_xlabel("K")
	left.set_ylabel("inertia", color=ACCENT)
	right = left.twinx()
	right.plot(ks, silhouette, marker="s", color=SECOND, label="silhouette")
	right.set_ylabel("silhouette", color=SECOND)
	left.set_title("K-means candidate K: elbow and silhouette")
	left.grid(alpha=0.25)
	return _save(fig, name)
