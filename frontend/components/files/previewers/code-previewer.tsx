'use client';

import { CodeBlock } from '@/components/chat/code-block';
import { getLanguageFromFile } from '@/lib/utils/file-utils';
import type { PreviewerProps } from './index';

export function CodePreviewer({ file, content }: PreviewerProps) {
  return (
    <div className="p-4">
      <CodeBlock
        code={content as string}
        language={getLanguageFromFile(file.original_name)}
        showLineNumbers={true}
        defaultExpanded={true}
      />
    </div>
  );
}

export default CodePreviewer;
