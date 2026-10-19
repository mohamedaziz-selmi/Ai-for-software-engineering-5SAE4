import React, { useState } from "react";

// A small Markdown renderer for the advisor's report. It builds React elements (never raw HTML), so text written
// by the model or found on a website cannot inject markup. It covers what the report uses: headings, nested
// bullet and numbered lists, code blocks, tables, quotes, bold, italics, inline code, links and [S1] citations.

// _italic_ only counts at word boundaries, so snake_case names such as my_var_name stay untouched.
const INLINE =
	/`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\[(S\d+)\]|\*\*([^*]+?)\*\*|\*([^*\s](?:[^*]*?[^*\s])?)\*|(?<!\w)_([^_\s](?:[^_]*?[^_\s])?)_(?!\w)/g;
const LIST_ITEM = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
const FENCE = /^\s*```/;
const HEADING = /^(#{1,6})\s+(.*)$/;
const RULE = /^\s*([-*_])\1{2,}\s*$/;
const TABLE_DIVIDER = /^\s*\|?[\s:|-]+\|[\s:|-]*$/;

export function renderInline(text, onCite, keyBase = "i") {
	const nodes = [];
	let last = 0;
	let index = 0;
	for (const match of text.matchAll(INLINE)) {
		if (match.index > last) nodes.push(text.slice(last, match.index));
		const key = `${keyBase}-${index++}`;
		if (match[1] !== undefined) {
			nodes.push(<code key={key}>{match[1]}</code>);
		} else if (match[3] !== undefined) {
			nodes.push(
				<a key={key} href={match[3]} target="_blank" rel="noreferrer noopener">
					{match[2]}
				</a>,
			);
		} else if (match[4] !== undefined) {
			nodes.push(
				onCite ? (
					<button key={key} type="button" className="md-cite" onClick={() => onCite(match[4])}>
						{match[4]}
					</button>
				) : (
					<span key={key} className="md-cite">{match[4]}</span>
				),
			);
		} else if (match[5] !== undefined) {
			nodes.push(<strong key={key}>{renderInline(match[5], onCite, key)}</strong>);
		} else {
			nodes.push(<em key={key}>{renderInline(match[6] ?? match[7], onCite, key)}</em>);
		}
		last = match.index + match[0].length;
	}
	if (last < text.length) nodes.push(text.slice(last));
	return nodes;
}

function startsBlock(line) {
	return FENCE.test(line) || HEADING.test(line) || RULE.test(line) || /^\s*>/.test(line) || LIST_ITEM.test(line);
}

function tableCells(line) {
	return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

function buildTree(flat) {
	const root = { indent: -1, children: [] };
	const stack = [root];
	for (const item of flat) {
		const node = { ...item, children: [] };
		while (stack.length > 1 && stack[stack.length - 1].indent >= node.indent) stack.pop();
		stack[stack.length - 1].children.push(node);
		stack.push(node);
	}
	return root.children;
}

export function parseBlocks(source) {
	const lines = source.replace(/\r\n?/g, "\n").split("\n");
	const blocks = [];
	let i = 0;
	while (i < lines.length) {
		const line = lines[i];
		if (!line.trim()) {
			i += 1;
			continue;
		}
		if (FENCE.test(line)) {
			const body = [];
			i += 1;
			while (i < lines.length && !FENCE.test(lines[i])) body.push(lines[i++]);
			i += 1; // the closing fence
			blocks.push({ type: "code", text: body.join("\n") });
			continue;
		}
		const heading = line.match(HEADING);
		if (heading) {
			blocks.push({ type: "heading", level: heading[1].length <= 3 ? 4 : 5, text: heading[2].trim() });
			i += 1;
			continue;
		}
		if (RULE.test(line)) {
			blocks.push({ type: "rule" });
			i += 1;
			continue;
		}
		if (/^\s*>/.test(line)) {
			const quote = [];
			while (i < lines.length && /^\s*>/.test(lines[i])) quote.push(lines[i++].replace(/^\s*>\s?/, ""));
			blocks.push({ type: "quote", lines: quote });
			continue;
		}
		if (line.trim().startsWith("|") && i + 1 < lines.length && TABLE_DIVIDER.test(lines[i + 1])) {
			const header = tableCells(line);
			const rows = [];
			i += 2;
			while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(tableCells(lines[i++]));
			blocks.push({ type: "table", header, rows });
			continue;
		}
		if (LIST_ITEM.test(line)) {
			const flat = [];
			while (i < lines.length) {
				const current = lines[i];
				const item = current.match(LIST_ITEM);
				if (item) {
					flat.push({
						indent: item[1].replace(/\t/g, "    ").length,
						ordered: /\d/.test(item[2]),
						number: Number.parseInt(item[2], 10),
						lines: [item[3]],
					});
					i += 1;
				} else if (!current.trim()) {
					// a blank line only ends the list when what follows is not an item or an indented continuation
					let next = i + 1;
					while (next < lines.length && !lines[next].trim()) next += 1;
					const continues = next < lines.length
						&& (LIST_ITEM.test(lines[next]) || (/^\s{2,}\S/.test(lines[next]) && !FENCE.test(lines[next])));
					if (!continues) break;
					i = next;
				} else if (/^\s+\S/.test(current) && !FENCE.test(current)) {
					flat[flat.length - 1].lines.push(current.trim());
					i += 1;
				} else {
					break;
				}
			}
			blocks.push({ type: "list", items: buildTree(flat) });
			continue;
		}
		const paragraph = [];
		while (i < lines.length && lines[i].trim() && (paragraph.length === 0 || !startsBlock(lines[i]))) {
			paragraph.push(lines[i++].trim());
		}
		blocks.push({ type: "paragraph", lines: paragraph });
	}
	return blocks;
}

function Lines({ lines, onCite, keyBase }) {
	return lines.map((text, index) => (
		<React.Fragment key={index}>
			{index > 0 && <br />}
			{renderInline(text, onCite, `${keyBase}-${index}`)}
		</React.Fragment>
	));
}

function ListTree({ nodes, onCite, keyBase }) {
	const ordered = nodes[0].ordered;
	const Tag = ordered ? "ol" : "ul";
	return (
		<Tag start={ordered && nodes[0].number > 1 ? nodes[0].number : undefined}>
			{nodes.map((node, index) => (
				<li key={index}>
					<Lines lines={node.lines} onCite={onCite} keyBase={`${keyBase}-${index}`} />
					{node.children.length > 0 && (
						<ListTree nodes={node.children} onCite={onCite} keyBase={`${keyBase}-${index}`} />
					)}
				</li>
			))}
		</Tag>
	);
}

function CodeBlock({ text }) {
	const [copied, setCopied] = useState(false);
	const copy = async () => {
		try {
			await navigator.clipboard.writeText(text);
			setCopied(true);
			window.setTimeout(() => setCopied(false), 1600);
		} catch {
			// the clipboard is blocked: the text can still be selected by hand
		}
	};
	return (
		<div className="md-code">
			<button type="button" className="md-code__copy" onClick={copy}>
				{copied ? "Copied" : "Copy"}
			</button>
			<pre><code>{text}</code></pre>
		</div>
	);
}

export function Markdown({ text, onCite }) {
	return (
		<div className="markdown">
			{parseBlocks(text).map((block, index) => {
				const key = `b${index}`;
				switch (block.type) {
					case "code":
						return <CodeBlock key={key} text={block.text} />;
					case "heading": {
						const Tag = `h${block.level}`;
						return <Tag key={key}>{renderInline(block.text, onCite, key)}</Tag>;
					}
					case "rule":
						return <hr key={key} />;
					case "quote":
						return (
							<blockquote key={key}>
								<Lines lines={block.lines} onCite={onCite} keyBase={key} />
							</blockquote>
						);
					case "table":
						return (
							<div className="md-table" key={key}>
								<table>
									<thead>
										<tr>
											{block.header.map((cell, cellIndex) => (
												<th key={cellIndex}>{renderInline(cell, onCite, `${key}-h${cellIndex}`)}</th>
											))}
										</tr>
									</thead>
									<tbody>
										{block.rows.map((row, rowIndex) => (
											<tr key={rowIndex}>
												{row.map((cell, cellIndex) => (
													<td key={cellIndex}>{renderInline(cell, onCite, `${key}-${rowIndex}-${cellIndex}`)}</td>
												))}
											</tr>
										))}
									</tbody>
								</table>
							</div>
						);
					case "list":
						return <ListTree key={key} nodes={block.items} onCite={onCite} keyBase={key} />;
					default:
						return (
							<p key={key}>
								<Lines lines={block.lines} onCite={onCite} keyBase={key} />
							</p>
						);
				}
			})}
		</div>
	);
}
