/** Render an accessible left-to-right tree and measure smooth SVG connectors. */
export function mountMindMap(container, roots) {
  container.replaceChildren();
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.classList.add('mind-links');
  svg.setAttribute('aria-hidden', 'true');
  container.append(svg);
  const edges = [];
  function branch(nodes, depth = 0) {
    const list = document.createElement('ul');
    list.className = 'mind-branches';
    for (const node of nodes) {
      const item = document.createElement('li');
      item.className = 'mind-branch';
      const label = document.createElement('button');
      label.className = `mind-node depth-${Math.min(depth, 2)}`;
      const title = document.createElement('span');
      title.textContent = node.title;
      label.append(title);
      item.append(label);
      if (node.children?.length && depth < 12) {
        const children = branch(node.children, depth + 1);
        const count = document.createElement('small');
        count.textContent = '−';
        label.append(count);
        label.setAttribute('aria-expanded', 'true');
        label.addEventListener('click', () => {
          children.hidden = !children.hidden;
          label.setAttribute('aria-expanded', String(!children.hidden));
          count.textContent = children.hidden ? `+${node.children.length}` : '−';
          requestAnimationFrame(draw);
        });
        item.append(children);
        for (const child of children.children) edges.push([label, child.firstElementChild]);
      } else {
        // Leaf nodes are informational, not actions.
        label.disabled = true;
      }
      list.append(item);
    }
    return list;
  }
  container.append(branch(roots));
  function draw() {
    if (!container.offsetWidth) return;
    const bounds = container.getBoundingClientRect();
    const factor = bounds.width / container.offsetWidth || 1;
    svg.setAttribute('width', container.offsetWidth);
    svg.setAttribute('height', container.offsetHeight);
    svg.replaceChildren();
    for (const [parent, child] of edges) {
      if (!child.getClientRects().length) continue;
      const a = parent.getBoundingClientRect(), b = child.getBoundingClientRect();
      const x1 = (a.right - bounds.left) / factor, y1 = (a.top + a.height / 2 - bounds.top) / factor;
      const x2 = (b.left - bounds.left) / factor, y2 = (b.top + b.height / 2 - bounds.top) / factor;
      const bend = (x2 - x1) * .5;
      const path = document.createElementNS(svg.namespaceURI, 'path');
      path.setAttribute('d', `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`);
      svg.append(path);
    }
  }
  const observer = new ResizeObserver(() => requestAnimationFrame(draw));
  observer.observe(container);
  requestAnimationFrame(draw);
  return () => observer.disconnect();
}
