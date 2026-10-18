import React, { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import * as THREE from "three";

const WORLD_HEIGHT = 10.4;

function makeTriangleGeometry(width, orientation = "up", sideways = false) {
	const height = (Math.sqrt(3) / 2) * width;
	let points =
		orientation === "up"
			? [
					[0, height / 2],
					[-width / 2, -height / 2],
					[width / 2, -height / 2],
				]
			: [
					[0, -height / 2],
					[-width / 2, height / 2],
					[width / 2, height / 2],
				];

	if (sideways) points = points.map(([x, y]) => [y, -x]);

	const geometry = new THREE.BufferGeometry();
	const positions = new Float32Array(points.flatMap(([x, y]) => [x, y, 0]));
	const uvs = new Float32Array(
		orientation === "up"
			? [0.5, 1, 0, 0, 1, 0]
			: [0.5, 0, 0, 1, 1, 1],
	);
	geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
	geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
	geometry.setIndex([0, 1, 2]);
	geometry.computeVertexNormals();
	return geometry;
}

function CursorLight() {
	const light = useRef(null);
	const target = useRef(new THREE.Vector3());
	const { camera, pointer, size } = useThree();

	useFrame(() => {
		if (!light.current) return;
		target.current.set(
			pointer.x * (size.width / size.height) * WORLD_HEIGHT / 2,
			(pointer.y * WORLD_HEIGHT) / 2,
			8,
		);
		light.current.position.lerp(target.current, 0.08);
		camera.updateMatrixWorld();
	});

	return (
		<>
			<ambientLight intensity={1.05} />
			<pointLight ref={light} position={[0, 0, 8]} intensity={30} distance={30} decay={2} />
		</>
	);
}

function TriangleTile({ geometry, edges, position, dark, lineColor, opacity = 0.1 }) {
	return (
		<group position={position}>
			<mesh geometry={geometry}>
				<meshStandardMaterial
					color={dark ? "#282832" : "#8f8ba8"}
					transparent
					opacity={opacity}
					side={THREE.DoubleSide}
					roughness={0.82}
				/>
			</mesh>
			<lineSegments geometry={edges}>
				<lineBasicMaterial color={lineColor} transparent opacity={dark ? 0.3 : 0.28} />
			</lineSegments>
		</group>
	);
}

function ProjectTriangle({
	project,
	index,
	position,
	width,
	sideways,
	onHover,
	onLeave,
	onSelect,
}) {
	const texture = useLoader(THREE.TextureLoader, project.images[0]);
	const orientation = index % 2 === 0 ? "up" : "down";
	const geometry = useMemo(
		() => makeTriangleGeometry(width, orientation, sideways),
		[width, orientation, sideways],
	);
	const edges = useMemo(() => new THREE.EdgesGeometry(geometry), [geometry]);
	const hovered = useRef(false);
	const hoverGroup = useRef(null);

	useFrame(() => {
		if (!hoverGroup.current) return;
		const targetZ = hovered.current ? 1.2 : 0;
		hoverGroup.current.position.z += (targetZ - hoverGroup.current.position.z) * 0.14;
		const targetScale = hovered.current ? 1.2 : 1;
		hoverGroup.current.scale.x += (targetScale - hoverGroup.current.scale.x) * 0.12;
		hoverGroup.current.scale.y += (targetScale - hoverGroup.current.scale.y) * 0.12;
	});

	return (
		<group ref={hoverGroup} position={position}>
			<mesh
				geometry={geometry}
				onPointerOver={(event) => {
					event.stopPropagation();
					hovered.current = true;
					event.nativeEvent.target.style.cursor = "pointer";
					onHover(project);
				}}
				onPointerOut={(event) => {
					event.stopPropagation();
					hovered.current = false;
					event.nativeEvent.target.style.cursor = "grab";
					onLeave(project);
				}}
				onClick={(event) => {
					event.stopPropagation();
					onSelect(project);
				}}
			>
				<meshStandardMaterial
					map={texture}
					color="#d0d0d4"
					roughness={0.72}
					metalness={0.02}
					side={THREE.DoubleSide}
				/>
			</mesh>
			<lineSegments geometry={edges}>
				<lineBasicMaterial color="#f0efff" transparent opacity={0.9} />
			</lineSegments>
		</group>
	);
}

function SceneContents({
	projects,
	dark,
	pan,
	onHover,
	onLeave,
	onSelect,
}) {
	const { size } = useThree();
	const aspect = size.width / Math.max(1, size.height);
	const scale =
		aspect <= 1.2 ? 0.9 : aspect >= 4 ? 2 : 0.9 + ((aspect - 1.2) / 2.8) * 1.1;
	const width = 4 * scale;
	const projectWidth = width;
	const height = (Math.sqrt(3) / 2) * width;
	const spacing = width / 2 + 0.07 * width;
	const projectSpacing = spacing;
	const sideways = aspect < 1.2;
	const panWorld = (pan * WORLD_HEIGHT) / Math.max(1, size.height);
	const upGeometry = useMemo(
		() => makeTriangleGeometry(width, "up", sideways),
		[width, sideways],
	);
	const downGeometry = useMemo(
		() => makeTriangleGeometry(width, "down", sideways),
		[width, sideways],
	);
	const upEdges = useMemo(() => new THREE.EdgesGeometry(upGeometry), [upGeometry]);
	const downEdges = useMemo(() => new THREE.EdgesGeometry(downGeometry), [downGeometry]);
	const centerX = (projects.length - 1) / 2;

	return (
		<>
			<CursorLight />
			<group position={sideways ? [0, panWorld, 0] : [panWorld, 0, 0]}>
				{Array.from({ length: 3 }, (_, row) => {
					const rowOffset = row - 1;
					return Array.from({ length: 40 }, (_, column) => {
						const down = column % 2 === (row % 2 === 1 ? 0 : 1);
						const geometry = down ? downGeometry : upGeometry;
						const horizontal = (19.5 - column) * spacing;
						const vertical = -rowOffset * (height + 0.9 * 0.07 * width);
						return (
							<TriangleTile
								key={`field-${row}-${column}`}
								geometry={geometry}
								edges={down ? downEdges : upEdges}
								position={sideways ? [vertical, horizontal, -0.12] : [horizontal, vertical, -0.12]}
								dark={dark}
								lineColor={dark ? "#666474" : "#f0efff"}
								opacity={dark ? 0.08 : 0.1}
							/>
						);
					});
				})}

				{projects.map((project, index) => {
					const centeredIndex = centerX - index;
					const horizontal = centeredIndex * projectSpacing;
					const vertical = index % 2 === 0 ? 0 : 0;
					return (
						<ProjectTriangle
							key={project.id}
							project={project}
							index={index}
							width={projectWidth}
							sideways={sideways}
							position={
								sideways
									? [vertical, horizontal, 0.02 + index * 0.001]
									: [horizontal, vertical, 0.02 + index * 0.001]
							}
							onHover={onHover}
							onLeave={onLeave}
							onSelect={onSelect}
						/>
					);
				})}
			</group>
		</>
	);
}

function CameraFit() {
	const { camera, size } = useThree();
	useFrame(() => {
		const zoom = size.height / WORLD_HEIGHT;
		if (camera.zoom !== zoom) {
			camera.zoom = zoom;
			camera.updateProjectionMatrix();
		}
	});
	return null;
}

export default function TriangleScene(props) {
	return (
		<Canvas
			className="triangle-canvas"
			orthographic
			camera={{ position: [0, 0, 30], zoom: 50, near: 0.1, far: 100 }}
			dpr={[1, 1.75]}
			gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
			onCreated={({ gl }) => {
				gl.setClearColor(0x000000, 0);
			}}
		>
			<CameraFit />
			<Suspense fallback={null}>
				<SceneContents {...props} />
			</Suspense>
		</Canvas>
	);
}
