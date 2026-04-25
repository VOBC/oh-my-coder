"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { CSSProperties } from "react";
import "highlight.js/styles/github.css";

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        code({ inline, className, children, ...props }: any) {
          const match = /language-(\w+)/.exec(className || "");
          if (!inline && match) {
            return (
              <SyntaxHighlighter
                style={oneDark as Record<string, CSSProperties>}
                language={match[1]} PreTag="div"
                customStyle={{ margin: "0.75rem 0", borderRadius: "0.5rem", fontSize: "0.85rem" }}
              >{String(children).replace(/\n$/, "")}</SyntaxHighlighter>
            );
          }
          return <code className={className} {...props}>{children}</code>;
        },
        a({ href, children }: any) {
          return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{children}</a>;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
