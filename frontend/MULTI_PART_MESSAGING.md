# Multi-Part Message Support - Implementation Guide

## Overview

This document describes the implementation of multi-part message support in the Claude Agent SDK Chat frontend. This feature enables sending messages that contain both text and images while maintaining full backward compatibility with existing string-based messages.

## What Was Changed

### 1. Type System Updates

#### `/frontend/types/index.ts`
- Added `ContentBlock` union type for text and image content
- Added `TextContentBlock` and `ImageContentBlock` interfaces
- Updated `ChatMessage.content` to accept `string | ContentBlock[]`

#### `/frontend/types/websocket.ts`
- Updated `ClientMessage.content` to accept `string | ContentBlock[]`
- Added comprehensive JSDoc documentation

### 2. Utility Functions

#### `/frontend/lib/content-utils.ts` (Already existed)
- `normalizeContent()` - Convert string to ContentBlock array
- `extractText()` - Extract text from any content format
- `extractImages()` - Get image blocks from content
- `hasImages()` - Check if content has images
- `isMultipartContent()` - Type guard for ContentBlock[]
- `toPreviewText()` - Generate text preview for UI

#### `/frontend/lib/message-utils.ts` (New file)
- `validateMessageContent()` - Comprehensive validation with detailed error messages
- `createTextBlock()` - Create text content blocks
- `createImageUrlBlock()` - Create image blocks from URLs
- `createImageBase64Block()` - Create image blocks from base64 data
- `createMultipartMessage()` - Build multi-part messages
- `fileToImageBlock()` - Convert File objects to image blocks
- `prepareMessageContent()` - Validate and prepare content for sending

### 3. WebSocket Layer

#### `/frontend/lib/websocket-manager.ts`
- Updated `sendMessage()` to accept `string | ContentBlock[]`
- Added comprehensive JSDoc with usage examples

#### `/frontend/hooks/use-websocket.ts`
- Updated wrapper `sendMessage()` to accept `string | ContentBlock[]`

### 4. Chat Logic

#### `/frontend/hooks/use-chat.ts`
- Updated `sendMessage()` to handle both string and ContentBlock[]
- Added validation using `validateMessageContent()`
- Added error handling with toast notifications
- Updated pending message handling with validation

### 5. UI Components

#### `/frontend/components/chat/chat-input.tsx`
- Updated `onSend` prop type to accept `string | ContentBlock[]`
- Added infrastructure for image handling (commented out for future use)
- Added state for image attachments
- Prepared file input ref and handlers
- **Note**: Full image UI is commented out, ready for future implementation

#### `/frontend/components/chat/user-message.tsx`
- Updated to use `extractText()` for content display
- Handles both string and ContentBlock[] formats

#### `/frontend/components/chat/assistant-message.tsx`
- Updated to use `extractText()` for content processing
- Handles both string and ContentBlock[] formats

#### `/frontend/components/chat/tool-use-message.tsx`
- Updated to use `extractText()` when accessing message content
- Handles interruption detection with ContentBlock support

#### `/frontend/components/chat/tool-result-message.tsx`
- Updated to use `extractText()` for content processing
- Handles both string and ContentBlock[] formats

## How to Use

### Sending Simple Text Messages (Unchanged)

```typescript
// Still works exactly as before
sendMessage('Hello, world!');
```

### Sending Multi-Part Messages (New)

```typescript
// Import types
import type { ContentBlock } from '@/types';
import { createMultipartMessage } from '@/lib/message-utils';

// Method 1: Direct content blocks
const content: ContentBlock[] = [
  { type: 'text', text: 'What do you see in this image?' },
  { type: 'image', source: { type: 'url', url: 'https://example.com/image.png' } }
];
sendMessage(content);

// Method 2: Using helper function
const message = createMultipartMessage('What do you see?', [
  { type: 'url', url: 'https://example.com/image.png' }
]);
sendMessage(message);

// Method 3: With base64 images
const message = createMultipartMessage('Analyze this chart', [
  { type: 'base64', data: 'iVBORw0KGgo...' }
]);
sendMessage(message);
```

### Validating Message Content

```typescript
import { validateMessageContent } from '@/lib/message-utils';

const result = validateMessageContent(content);
if (!result.valid) {
  console.error(result.error);
  // Handle validation error
}
```

### Processing Received Messages

All message display components now automatically handle both formats:

```typescript
// Components handle this internally
import { extractText } from '@/lib/content-utils';

const textContent = extractText(message.content);
// Returns string for both string and ContentBlock[] inputs
```

## Backward Compatibility

✅ **100% backward compatible** - All existing code continues to work:

- String messages work everywhere
- No breaking changes to APIs
- Components auto-detect content type
- Validation accepts both formats
- WebSocket handles both formats

## Migration for Existing Code

### No Migration Required

Existing code continues to work without changes:

```typescript
// This still works perfectly
sendMessage('Hello, world!');
```

### Optional Migration

If you want to add image support:

```typescript
// Before
const handleSend = (text: string) => {
  sendMessage(text);
};

// After (with optional image support)
const handleSend = (content: string | ContentBlock[]) => {
  sendMessage(content);
};
```

## Image Upload Implementation (Future)

The infrastructure is ready for image uploads. To enable:

1. **Uncomment image upload button** in `chat-input.tsx` (lines ~93-104)
2. **Implement `handleImageSelect`** function:
   ```typescript
   const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
     const files = e.target.files;
     if (!files) return;

     const newImages = await Promise.all(
       Array.from(files).map(fileToImageBlock)
     );

     setImages(prev => [...prev, ...newImages]);
   };
   ```
3. **Uncomment image preview** section (lines ~178-188)
4. **Add image preview component** if needed

## Validation Rules

### Text Content
- Cannot be empty or whitespace only
- Must be a string

### Image Content
- Must have `source` object
- Source type must be `'base64'` or `'url'`
- Base64 images must include `data` property
- URL images must include `url` property
- No automatic size limits (add validation if needed)

### ContentBlock Arrays
- Must be non-empty
- Each block must be valid
- Can mix text and image blocks

## Error Handling

All validation errors are user-friendly:

```typescript
// Empty string
"Message content cannot be empty"

// Empty array
"Content blocks must be a non-empty array"

// Invalid image
"Image source type must be either 'base64' or 'url'"

// Missing required fields
"Base64 image must include data property"
```

Errors are displayed via toast notifications for better UX.

## Testing

### Manual Testing Checklist

- [ ] Send simple text message
- [ ] Send multi-part message with text + image (URL)
- [ ] Send multi-part message with text + image (base64)
- [ ] Send message with only text block
- [ ] Send message with multiple images
- [ ] Test validation with empty content
- [ ] Test validation with invalid content blocks
- [ ] Test that old string messages still work
- [ ] Test message display in user-message component
- [ ] Test message display in assistant-message component
- [ ] Test message display in tool-result-message component
- [ ] Test interruption detection in tool-use-message

### Example Test Code

```typescript
// Test 1: Simple text
sendMessage('Hello world!');

// Test 2: Multi-part with URL
sendMessage([
  { type: 'text', text: 'Describe this image' },
  { type: 'image', source: { type: 'url', url: 'https://picsum.photos/200' } }
]);

// Test 3: Validation error
sendMessage(''); // Should show error toast

// Test 4: Invalid content block
sendMessage([{ type: 'text' }]); // Missing 'text' property
```

## Performance Considerations

- **No overhead** for string messages (code path is unchanged)
- **Validation** is fast and synchronous
- **Base64 images** increase message size (consider compression)
- **URL images** are just URLs (no data transfer overhead)

## Security Considerations

- **Base64 images** are sent as-is (no sanitization)
- **URL images** should be validated server-side
- **File size limits** should be enforced (future enhancement)
- **Image type validation** should be added (future enhancement)

## Future Enhancements

1. **Image Upload UI**
   - Drag-and-drop support
   - Paste from clipboard
   - File selection dialog
   - Image preview with remove option

2. **Image Processing**
   - Client-side compression
   - Format conversion (WebP, etc.)
   - Size limits and warnings
   - Type validation

3. **Enhanced UX**
   - Loading states for uploads
   - Progress indicators
   - Error recovery
   - Retry logic

4. **Additional Content Types**
   - File attachments (PDF, docs, etc.)
   - Audio recordings
   - Video clips
   - Structured data (JSON, etc.)

## Related Files

- `/frontend/types/index.ts` - Core type definitions
- `/frontend/types/websocket.ts` - WebSocket message types
- `/frontend/lib/content-utils.ts` - Content processing utilities
- `/frontend/lib/message-utils.ts` - Message creation and validation
- `/frontend/lib/websocket-manager.ts` - WebSocket connection manager
- `/frontend/hooks/use-websocket.ts` - WebSocket React hook
- `/frontend/hooks/use-chat.ts` - Chat logic hook
- `/frontend/components/chat/chat-input.tsx` - Message input component
- `/frontend/components/chat/*-message.tsx` - Message display components

## Support

For questions or issues:
1. Check this guide first
2. Review inline JSDoc comments in source files
3. Check the migration guide in `/frontend/lib/message-utils.ts`
4. Consult backend API documentation for WebSocket format

## Changelog

### 2025-01-30
- ✅ Initial implementation of multi-part message support
- ✅ Type system updates (ContentBlock, etc.)
- ✅ Validation utilities
- ✅ WebSocket layer updates
- ✅ Component updates for content handling
- ✅ Backward compatibility maintained
- ⏳ Image UI infrastructure (ready for implementation)
