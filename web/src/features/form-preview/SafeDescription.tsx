import { createElement, Fragment, type ReactNode } from 'react';
import { hasDescriptionText } from './descriptionUtils';

const allowedTags = new Set([
  'P',
  'UL',
  'OL',
  'LI',
  'STRONG',
  'B',
  'EM',
  'I',
  'BR',
]);
const discardedTags = new Set(['SCRIPT', 'STYLE', 'IMG']);

function renderNode(node: Node, key: string): ReactNode {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent;
  if (node.nodeType !== Node.ELEMENT_NODE) return null;

  const element = node as Element;
  if (discardedTags.has(element.tagName)) return null;

  const children = Array.from(element.childNodes).map((child, index) =>
    renderNode(child, `${key}-${index}`),
  );
  if (allowedTags.has(element.tagName)) {
    return createElement(element.tagName.toLowerCase(), { key }, ...children);
  }

  return createElement(Fragment, { key }, ...children);
}

export function SafeDescription({ markup }: { markup?: string }) {
  if (!markup || !hasDescriptionText(markup)) return null;

  const document = new DOMParser().parseFromString(markup, 'text/html');
  return <>{Array.from(document.body.childNodes).map((node, index) => renderNode(node, String(index)))}</>;
}