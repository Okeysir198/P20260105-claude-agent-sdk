# Multi-Part Content Support - Migration Guide

## Overview

The frontend types have been updated to support multi-part message content (text + images) while maintaining backward compatibility with existing string-based messages.

## What Changed

### 1. New Types (`frontend/types/index.ts`)

```typescript
export type ContentBlock = TextContentBlock | ImageContentBlock;

export interface TextContentBlock {
  type: 'text';
  text: string;
}

export interface ImageContentBlock {
  type: 'image';
  source: {
    type: 'base64' | 'url';
    data?: string;
    url?: string;
  };
}

export interface ChatMessage {
  // ... other fields
  content: string | ContentBlock[];  // Now supports both formats
}
```

### 2. Updated Related Types

- **`HistoryMessage`** (`types/api.ts`): Content field now supports `string | any` for backward compatibility
- **`ClientMessage`** (`types/websocket.ts`): Content field supports multi-part for WebSocket messages

### 3. New Utility Functions (`frontend/lib/content-utils.ts`)

Helper functions to work with multi-part content:

```typescript
import { normalizeContent, extractText, extractImages, hasImages, isMultipartContent, toPreviewText } from '@/lib/content-utils';

// Normalize string/array to always return ContentBlock[]
const blocks = normalizeContent(message.content);

// Extract just the text portion
const text = extractText(message.content);

// Get all images
const images = extractImages(message.content);

// Check if has images
if (hasImages(message.content)) {
  // Handle images
}

// Create preview text
const preview = toPreviewText(message.content, 100);
```

## TypeScript Compilation Status

**Current Status**: Type errors exist in components that haven't been migrated yet.

### Components Requiring Updates

1. **`components/chat/user-message.tsx`** (line 15)
   - Currently: `{message.content}`
   - Fix: Use `{extractText(message.content)}` or iterate through blocks

2. **`components/chat/assistant-message.tsx`** (lines 23, 26, 29, 35, 198)
   - Currently: String operations on `message.content`
   - Fix: Use `extractText(message.content)` before string operations

3. **`components/chat/tool-use-message.tsx`** (lines 54, 55, 97, 139)
   - Currently: Expects `message.content` to be string
   - Fix: Add type guard or use utility functions

4. **`components/chat/tool-result-message.tsx`** (lines 548, 549, 554, 556, 689)
   - Currently: String operations on `message.content`
   - Fix: Use `extractText(message.content)` before string operations

## Migration Strategy

### Phase 1: Type Updates ✅ (Complete)
- Updated `ChatMessage` type to support `string | ContentBlock[]`
- Created utility functions for content manipulation
- Updated related types (HistoryMessage, ClientMessage)

### Phase 2: Component Migration (Next Steps)
For each component, choose one of these approaches:

**Option A: Quick Backward-Compat (Minimal Changes)**
```typescript
import { extractText } from '@/lib/content-utils';

// In component
const content = extractText(message.content);
// Use content as before
```

**Option B: Full Multi-Part Support**
```typescript
import { normalizeContent, isMultipartContent } from '@/lib/content-utils';
import type { ContentBlock } from '@/types';

// In component
const blocks = normalizeContent(message.content);

return (
  <div>
    {blocks.map((block, i) => (
      <Fragment key={i}>
        {block.type === 'text' && <p>{block.text}</p>}
        {block.type === 'image' && <img src={block.source.type === 'url' ? block.source.url : `data:image/png;base64,${block.source.data}`} />}
      </Fragment>
    ))}
  </div>
);
```

### Phase 3: Testing
After component migration:
1. Test text-only messages (backward compat)
2. Test multi-part messages (text + image)
3. Test image-only messages
4. Verify TypeScript compilation passes
5. Test in browser with real WebSocket messages

## Example: Migrating UserMessage Component

**Before:**
```typescript
export function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="...">
      <p>{message.content}</p>
    </div>
  );
}
```

**After (Option A - Quick Fix):**
```typescript
import { extractText } from '@/lib/content-utils';

export function UserMessage({ message }: UserMessageProps) {
  const text = extractText(message.content);

  return (
    <div className="...">
      <p>{text}</p>
    </div>
  );
}
```

**After (Option B - Full Support):**
```typescript
import { normalizeContent } from '@/lib/content-utils';
import type { ContentBlock } from '@/types';

export function UserMessage({ message }: UserMessageProps) {
  const blocks = normalizeContent(message.content);

  return (
    <div className="...">
      {blocks.map((block, i) => (
        <div key={i}>
          {block.type === 'text' && (
            <p>{block.text}</p>
          )}
          {block.type === 'image' && (
            <img
              src={
                block.source.type === 'url'
                  ? block.source.url
                  : `data:image/${block.source.media_type || 'png'};base64,${block.source.data}`
              }
              alt="Uploaded image"
              className="rounded-lg max-w-full"
            />
          )}
        </div>
      ))}
    </div>
  );
}
```

## Backend Integration Notes

The backend WebSocket handler should send messages in this format:

```typescript
// For text-only (backward compat)
{ type: 'text_delta', text: 'Hello world' }

// For multi-part (new)
{
  type: 'text_delta',
  content: [
    { type: 'text', text: 'What do you see?' },
    { type: 'image', source: { type: 'url', url: 'https://...' } }
  ]
}
```

## Validation Checklist

- [x] Types updated with backward compatibility
- [x] Utility functions created
- [ ] Components migrated (choose one option per component)
- [ ] TypeScript compilation passes
- [ ] Text-only messages work
- [ ] Multi-part messages render correctly
- [ ] Images display properly
- [ ] Error handling for malformed content
- [ ] Performance testing with large messages

## Next Steps

1. **Immediate**: Run TypeScript compiler to see all type errors
   ```bash
   cd frontend && npx tsc --noEmit
   ```

2. **Choose Migration Strategy**:
   - Quick migration: Use `extractText()` everywhere (1-2 hours)
   - Full migration: Implement multi-part rendering in user/assistant messages (4-6 hours)

3. **Implement**: Update components following examples above

4. **Test**: Verify all message types work correctly

5. **Deploy**: Test in production with real users

## Files Modified

- `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/types/index.ts`
- `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/types/api.ts`
- `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/types/websocket.ts`
- `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/lib/content-utils.ts` (NEW)
