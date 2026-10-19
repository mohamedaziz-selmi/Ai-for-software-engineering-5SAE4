import { useEffect, useState } from "react";

// Staff back-office: the day's orders for one shop.
export default function StaffOrders({ shopId, day }) {
	const [orders, setOrders] = useState([]);

	useEffect(() => {
		fetch(`/api/staff/orders?shop=${shopId}&day=${day}`).then((r) => r.json()).then(setOrders);
	}, [shopId, day]);

	// Newest orders first, so staff see what just came in.
	const sorted = [...orders].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

	async function markReady(id) {
		await fetch(`/api/staff/orders/${id}/ready`, { method: "POST" });
		setOrders((list) => list.map((o) => (o.id === id ? { ...o, status: "ready" } : o)));
	}

	return (
		<section aria-labelledby="orders-title">
			<h1 id="orders-title">Commandes du {day}</h1>
			<a href={`/api/staff/orders.csv?shop=${shopId}&day=${day}`} download>Exporter en CSV</a>
			<table>
				<thead>
					<tr><th scope="col">N°</th><th scope="col">Client</th><th scope="col">Créneau</th><th scope="col">Statut</th><th scope="col"><span className="sr-only">Action</span></th></tr>
				</thead>
				<tbody>
					{sorted.map((o) => (
						<tr key={o.id}>
							<td>{o.number}</td>
							<td>{o.customerName}</td>
							<td>{o.slotStart}</td>
							<td>{o.status === "ready" ? "Prête" : "En préparation"}</td>
							<td>{o.status !== "ready" && <button type="button" onClick={() => markReady(o.id)}>Marquer prête</button>}</td>
						</tr>
					))}
				</tbody>
			</table>
		</section>
	);
}
