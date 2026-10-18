(() => {
	const maxShiftRatio = 0.28;
	const worldUnitsPerPixel = 0.025;
	const canvases = new WeakMap();
	let pendingDrag = null;
	let drag = null;
	let animationFrame = 0;

	const getState = (canvas) => {
		let state = canvases.get(canvas);
		if (!state) {
			state = { shift: 0, camera: null, cameraStartX: 0 };
			canvases.set(canvas, state);
		}

		const camera = window.__triangleDragCamera;
		if (camera && state.camera !== camera) {
			state.camera = camera;
			state.cameraStartX = camera.position.x + state.shift * worldUnitsPerPixel;
		}
		return state;
	};

	const setShift = (canvas, shift) => {
		const limit = canvas.parentElement.clientWidth * maxShiftRatio;
		const state = getState(canvas);
		state.shift = Math.max(-limit, Math.min(limit, shift));
		if (state.camera) {
			state.camera.position.x = state.cameraStartX + state.shift * worldUnitsPerPixel;
			state.camera.updateMatrixWorld();
		}
	};

	const stopAnimation = () => {
		if (animationFrame) {
			cancelAnimationFrame(animationFrame);
			animationFrame = 0;
		}
	};

	const glide = (canvas, velocity) => {
		if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

		const state = getState(canvas);
		velocity *= 0.35;
		const tick = () => {
			velocity *= 0.84;
			if (Math.abs(velocity) < 0.15) {
				animationFrame = 0;
				return;
			}

			const previousShift = state.shift;
			setShift(canvas, previousShift + velocity);
			if (state.shift === previousShift) {
				animationFrame = 0;
				return;
			}
			animationFrame = requestAnimationFrame(tick);
		};

		animationFrame = requestAnimationFrame(tick);
	};

	document.addEventListener(
		"pointerover",
		(event) => {
			const container = event.target.closest(".expContainer");
			const canvas = container && container.querySelector("canvas");
			if (canvas) canvas.style.cursor = "grab";
		},
		true,
	);

	document.addEventListener(
		"pointerdown",
		(event) => {
			const container = event.target.closest(".expContainer");
			const canvas = container && container.querySelector("canvas");
			if (!canvas || event.button !== 0 || drag || pendingDrag) return;

			stopAnimation();
			const state = getState(canvas);
			pendingDrag = {
				canvas,
				container,
				pointerId: event.pointerId,
				startX: event.clientX,
				startShift: state.shift,
				lastX: event.clientX,
				lastTime: performance.now(),
				velocity: 0,
			};
		},
		true,
	);

	document.addEventListener(
		"pointermove",
		(event) => {
			if (!drag) {
				if (!pendingDrag || event.pointerId !== pendingDrag.pointerId) return;
				if (Math.abs(event.clientX - pendingDrag.startX) < 6) return;

				drag = pendingDrag;
				pendingDrag = null;
				drag.canvas.style.cursor = "grabbing";
				drag.container.setPointerCapture(event.pointerId);
			} else if (event.pointerId !== drag.pointerId) {
				return;
			}

			const now = performance.now();
			const elapsed = now - drag.lastTime;
			if (elapsed > 0) drag.velocity = (event.clientX - drag.lastX) / elapsed * 16;
			drag.lastX = event.clientX;
			drag.lastTime = now;
			setShift(drag.canvas, drag.startShift + event.clientX - drag.startX);
			event.preventDefault();
			event.stopPropagation();
			event.stopImmediatePropagation();
		},
		true,
	);

	const finishDrag = (event) => {
		if (pendingDrag && (!event || event.pointerId === pendingDrag.pointerId)) {
			pendingDrag = null;
			return;
		}
		if (!drag || (event && event.pointerId !== drag.pointerId)) return;

		const { canvas, container, velocity } = drag;
		drag = null;
		canvas.style.cursor = "grab";
		if (container.hasPointerCapture(event.pointerId)) {
			container.releasePointerCapture(event.pointerId);
		}
		event.preventDefault();
		event.stopPropagation();
		event.stopImmediatePropagation();
		glide(canvas, velocity);
	};

	document.addEventListener("pointerup", finishDrag, true);
	document.addEventListener("pointercancel", finishDrag, true);

	document.querySelectorAll(".expContainer canvas").forEach((canvas) => {
		canvas.style.cursor = "grab";
	});
})();
