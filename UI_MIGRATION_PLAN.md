# Complete UI Migration Plan - Parallel Execution Strategy

## Overview
Copy 100% of UI components and design from `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend` to `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend`

**Critical Requirement**: Execute all tracks in parallel using multiple subagents for maximum efficiency.

---

## Track 1: Dependencies & Setup (MUST RUN FIRST)

### Agent: dependencies-setup
**Dependencies**: None (must run first)

**Tasks**:
1. Install missing npm packages:
   ```bash
   npm install framer-motion react-virtuoso usehooks-ts
   npm install @radix-ui/react-dropdown-menu @radix-ui/react-hover-card @radix-ui/react-scroll-area @radix-ui/react-select @radix-ui/react-separator @radix-ui/react-switch @radix-ui/react-tabs @radix-ui/react-tooltip
   npm install fast-deep-equal sonner
   ```

2. Verify installation:
   - Check package.json for all dependencies
   - Run `npm list` to confirm

**Deliverable**: All dependencies installed successfully

---

## Track 2: UI Base Components (26 files)

### Agent: ui-base-components
**Dependencies**: Track 1 (dependencies)

**Source**: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/components/ui/`
**Target**: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/components/ui/`

**Files to Copy** (copy all, replace existing):

1. `alert.tsx` - NEW (alert banner component)
2. `alert-dialog.tsx` - NEW (confirmation dialog)
3. `avatar.tsx` - REPLACE
4. `badge.tsx` - REPLACE (already exists, update)
5. `button.tsx` - REPLACE
6. `button-group.tsx` - NEW (button group layout)
7. `card.tsx` - REPLACE
8. `carousel.tsx` - NEW (image carousel)
9. `checkbox.tsx` - NEW
10. `collapsible.tsx` - REPLACE
11. `command.tsx` - REPLACE
12. `dialog.tsx` - REPLACE
13. `dropdown-menu.tsx` - REPLACE
14. `hover-card.tsx` - NEW
15. `input-group.tsx` - NEW
16. `input.tsx` - REPLACE
17. `label.tsx` - NEW
18. `progress.tsx` - NEW
19. `scroll-area.tsx` - REPLACE
20. `select.tsx` - NEW
21. `separator.tsx` - REPLACE
22. `sheet.tsx` - REPLACE
23. `skeleton.tsx` - REPLACE
24. `switch.tsx` - NEW
25. `table.tsx` - NEW
26. `tabs.tsx` - REPLACE
27. `textarea.tsx` - REPLACE
28. `tooltip.tsx` - REPLACE

**Instructions**:
- Copy all files from source to target
- Update import paths if needed (e.g., `@/components/ui/*`)
- Ensure all Radix UI imports match installed packages

**Deliverable**: 28 UI base components copied and working

---

## Track 3: Main Chat Layout (3 files)

### Agent: main-chat-layout
**Dependencies**: Track 1 (dependencies), Track 2 (UI components)

**Source**: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/components/`
**Target**: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/components/chat/`

**Files to Copy**:

1. **`chat.tsx`** → `chat/chat.tsx` (NEW - main container)
   - Key structure: ChatHeader, Messages, MultimodalInput
   - Artifact support
   - Streaming with useChat hook
   - Copy entire file and adapt to current project structure

2. **`chat-header.tsx`** → `chat/chat-header.tsx` (REPLACE)
   - Sticky header with `sticky top-0`
   - Sidebar toggle, new chat, model selector
   - Memory toggle switch
   - Responsive design

3. **`messages.tsx`** → `chat/messages.tsx` (REPLACE message-list.tsx)
   - Replace Virtuoso with simple scroll
   - Structure: `max-w-4xl mx-auto` with `gap-4 md:gap-6`
   - Auto-scroll to bottom

**Instructions**:
- Copy chat.tsx as new file
- Replace chat-header.tsx completely
- Replace message-list.tsx with messages.tsx logic
- Update imports for current project hooks (`use-claude-chat.ts`)

**Deliverable**: Main chat layout components updated

---

## Track 4: Message Components (6 files)

### Agent: message-components
**Dependencies**: Track 1 (dependencies), Track 2 (UI components)

**Source**: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/components/`
**Target**: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/components/chat/`

**Files to Copy/Update**:

1. **`message.tsx`** → `chat/message.tsx` (REPLACE message-item.tsx)
   - Add Framer Motion spring animation:
   ```tsx
   <motion.div
     initial={{ opacity: 0, y: 20 }}
     animate={{ opacity: 1, y: 0 }}
     transition={{ type: "spring", stiffness: 500, damping: 30, delay: 0.05 }}
     className="group/message w-full"
   >
   ```
   - User messages: blue (#006cff), right-aligned, `rounded-2xl`
   - Assistant messages: transparent, left-aligned with SparklesIcon avatar

2. **`message-actions.tsx`** → `chat/message-actions.tsx` (REPLACE)
   - Hover reveal: `opacity-0 group-hover/message:opacity-100`
   - Copy, edit, delete, regenerate actions
   - Use lucide-react icons

3. **`message-editor.tsx`** → `chat/message-editor.tsx` (NEW)
   - In-place message editing
   - Submit edited message

4. **`message-reasoning.tsx`** → `chat/message-reasoning.tsx` (NEW)
   - Collapsible reasoning display
   - For Claude's extended thinking

5. **Update `user-message.tsx`** (MODIFY existing)
   - Apply blue background: `backgroundColor: "#006cff"`
   - Right-align: `justify-end`
   - Rounded: `rounded-2xl`
   - White text

6. **Update `assistant-message.tsx`** (MODIFY existing)
   - Transparent background
   - Left-align: `justify-start`
   - Add SparklesIcon avatar:
   ```tsx
   <div className="-mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-background ring-1 ring-border">
     <Sparkles size={14} className="text-primary" />
   </div>
   ```

**Deliverable**: All message components updated with reference design

---

## Track 5: Input Components (4 files)

### Agent: input-components
**Dependencies**: Track 1 (dependencies), Track 2 (UI components), Track 7 (Elements)

**Source**: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/components/`
**Target**: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/components/chat/`

**Files to Copy/Update**:

1. **`multimodal-input.tsx`** → `chat/multimodal-input.tsx` (REPLACE chat-input.tsx)
   - File upload support (drag & drop, paste, click)
   - Attachment preview with remove
   - Auto-resize textarea (min 44px, max 200px)
   - Model selector dropdown
   - Submit/Stop button toggle
   - Uses PromptInput from elements

2. **`submit-button.tsx`** → `chat/submit-button.tsx` (NEW)
   - ArrowUp icon for submit
   - Stop icon for cancel
   - Loading states

3. **`suggested-actions.tsx`** → `chat/suggested-actions.tsx` (NEW)
   - Quick action buttons
   - Only show when messages.length === 0

4. **`preview-attachment.tsx`** → `chat/preview-attachment.tsx` (NEW)
   - Attachment thumbnail preview
   - Remove button
   - Uploading state

**Deliverable**: Advanced input system with file attachments

---

## Track 6: Sidebar Components (5 files)

### Agent: sidebar-components
**Dependencies**: Track 1 (dependencies), Track 2 (UI components)

**Source**: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/components/`
**Target**: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/components/session/`

**Files to Copy**:

1. **`app-sidebar.tsx`** → `session/app-sidebar.tsx` (REPLACE session-sidebar.tsx)
   - Collapsible with state management
   - Chat history grouped by date
   - Delete all chats button
   - User navigation footer
   - Mobile responsive

2. **`sidebar-history.tsx`** → `session/sidebar-history.tsx` (NEW)
   - Infinite scroll pagination
   - Date grouping
   - Uses SWR for data fetching

3. **`sidebar-history-item.tsx`** → `session/sidebar-history-item.tsx` (REPLACE session-item.tsx)
   - Hover effects: `hover:bg-accent transition-colors`
   - Delete button on hover
   - Active state styling

4. **`sidebar-toggle.tsx`** → `session/sidebar-toggle.tsx` (NEW)
   - Collapse/expand sidebar
   - Smooth transitions

5. **`sidebar-user-nav.tsx`** → `session/sidebar-user-nav.tsx` (NEW)
   - User profile section
   - Sign out button
   - Settings link

**Deliverable**: Complete sidebar system with collapsible states

---

## Track 7: Element Components (16 files)

### Agent: element-components
**Dependencies**: Track 1 (dependencies), Track 2 (UI components)

**Source**: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/components/elements/`
**Target**: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/components/elements/` (CREATE NEW DIRECTORY)

**Files to Copy**:

1. `actions.tsx` - Action buttons (already exists in chat/, move to elements/)
2. `code-block.tsx` - Code syntax highlighting (already exists, move to elements/)
3. `tool.tsx` - Tool call display (already exists, move to elements/)
4. `conversation.tsx` - NEW - Conversation flow element
5. `image-preview.tsx` - NEW - Image preview component
6. `json-viewer.tsx` - NEW - JSON syntax highlighting
7. `loader.tsx` - NEW - Loading spinner
8. `message.tsx` - NEW - Message content wrapper
9. `model-selector.tsx` - NEW - Model selection dropdown
10. `prompt-input.tsx` - NEW - Structured input with toolbar
11. `reasoning.tsx` - NEW - Reasoning display
12. `response.tsx` - NEW - Response element
13. `source.tsx` - NEW - Source/citation element
14. `suggestion.tsx` - NEW - Suggestion chips
15. `task.tsx` - NEW - Task element
16. `web-preview.tsx` - NEW - Web page preview

**Instructions**:
- Create `components/elements/` directory if it doesn't exist
- Copy all 16 files
- Move existing files from chat/ to elements/
- Update import paths in all files

**Deliverable**: Complete elements library

---

## Track 8: Artifact Components (4 files - Optional)

### Agent: artifact-components
**Dependencies**: Track 1 (dependencies), Track 2 (UI components), Track 7 (Elements)

**Source**: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/components/`
**Target**: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/components/artifact/` (CREATE NEW DIRECTORY)

**Files to Copy**:

1. **`artifact.tsx`** → `artifact/artifact.tsx` (NEW)
   - Floating artifact panel
   - Document, code, image, sheet support
   - Collapsible/expandable

2. **`artifact-actions.tsx`** → `artifact/artifact-actions.tsx` (NEW)
   - Artifact manipulation buttons

3. **`artifact-close-button.tsx`** → `artifact/artifact-close-button.tsx` (NEW)
   - Close button

4. **`artifact-messages.tsx`** → `artifact/artifact-messages.tsx` (NEW)
   - Artifact message history

**Instructions**:
- Create `components/artifact/` directory
- Copy all 4 files
- Update imports

**Deliverable**: Artifact system (optional enhancement)

---

## Track 9: Special Components (4 files)

### Agent: special-components
**Dependencies**: Track 1 (dependencies), Track 2 (UI components)

**Files to Update**:

1. **`agent-selector.tsx`** (reference) → Update `agent/agent-selector-grid.tsx`
   - Grid layout: `grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2`
   - Card-based design with icons
   - Hover effects

2. **`greeting.tsx`** (reference) → Update `chat/welcome-screen.tsx`
   - Animated welcome message
   - Suggested actions
   - Agent branding

3. **`icons.tsx`** (reference) → Create `components/icons.tsx` (NEW)
   - Comprehensive icon library
   - Export all icons from single file
   - Uses lucide-react

4. **`data-stream-provider.tsx`** → Create `components/chat/data-stream-provider.tsx` (NEW)
   - Context for streaming data
   - Used by message components

**Deliverable**: Special components updated

---

## Track 10: Styling & Theming (3 files)

### Agent: styling-theming
**Dependencies**: None (can run in parallel with Track 1)

**Files to Update**:

1. **`globals.css`**
   - Source: `/home/ct-admin/Documents/Langgraph/P20251220-Langchain-agents/agent00_chat_app/frontend/app/globals.css`
   - Target: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/styles/globals.css`
   - **CRITICAL**: Replace entire file with HSL color system:
   ```css
   :root {
     --background: hsl(40 23% 97%);
     --foreground: hsl(30 10% 15%);
     --primary: hsl(15 62% 60%);
     --primary-foreground: hsl(0 0% 100%);
     --secondary: hsl(30 10% 94%);
     --secondary-foreground: hsl(30 10% 25%);
     --muted: hsl(30 8% 95%);
     --muted-foreground: hsl(30 5% 45%);
     --accent: hsl(30 15% 93%);
     --accent-foreground: hsl(30 10% 20%);
     --border: hsl(30 10% 88%);
     --input: hsl(30 10% 88%);
     --ring: hsl(15 62% 60%);
     --radius: 0.625rem;
   }
   ```
   - Include all CSS utilities (safe-area, scrollbar, etc.)
   - Keep existing KaTeX and highlight.js imports

2. **`tailwind.config.ts`**
   - Source: Check if exists (reference uses Tailwind v4)
   - Target: `/home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend/tailwind.config.ts`
   - Add HSL color support if using Tailwind v3
   - Add animation keyframes:
   ```ts
   animations: {
     "spring": "spring 0.5s ease-out",
   },
   keyframes: {
     spring: {
       "0%": { opacity: 0, transform: "translateY(20px)" },
       "100%": { opacity: 1, transform: "translateY(0)" },
     }
   }
   ```

3. **Update `app/layout.tsx` imports**
   - Import globals.css from correct path
   - Ensure font imports match

**Deliverable**: Complete HSL design system implemented

---

## Track 11: Utility Functions & Libraries (2 files)

### Agent: utilities-lib
**Dependencies**: None (can run in parallel)

**Files to Check/Update**:

1. **`lib/utils.ts`**
   - Ensure `cn()` function exists:
   ```ts
   import { clsx, type ClassValue } from "clsx"
   import { twMerge } from "tailwind-merge"

   export function cn(...inputs: ClassValue[]) {
     return twMerge(clsx(inputs))
   }
   ```

2. **`lib/types.ts`** - Check if ChatMessage type exists:
   ```ts
   export interface ChatMessage {
     id: string;
     role: "user" | "assistant" | "system";
     parts: MessagePart[];
     createdAt?: Date;
   }

   export type MessagePart =
     | { type: "text"; text: string }
     | { type: "tool-*"; toolCallId: string; input: any; output?: any; state: string }
     | { type: "file"; url: string; name: string; mediaType: string };
   ```

**Deliverable**: Utility functions updated

---

## Track 12: Main Page Integration

### Agent: page-integration
**Dependencies**: Track 3 (Main Chat Layout), Track 6 (Sidebar), Track 10 (Styling)

**Files to Update**:

1. **`app/page.tsx`**
   - Update imports to use new Chat component
   - Integrate sidebar state
   - Ensure WebSocket connection works
   - Add agent selection

**Deliverable**: Main page using new components

---

## Execution Order & Parallel Strategy

### Phase 1: Foundation (Can run in parallel)
- **Track 1**: Dependencies & Setup (MUST COMPLETE FIRST)
- **Track 10**: Styling & Theming (can run with Track 1)
- **Track 11**: Utilities (can run with Track 1)

### Phase 2: Component Libraries (Can run in parallel after Phase 1)
- **Track 2**: UI Base Components (26 files)
- **Track 7**: Element Components (16 files)
- **Track 8**: Artifact Components (4 files - optional)

### Phase 3: Feature Components (Can run in parallel after Phase 2)
- **Track 3**: Main Chat Layout (3 files)
- **Track 4**: Message Components (6 files)
- **Track 5**: Input Components (4 files)
- **Track 6**: Sidebar Components (5 files)
- **Track 9**: Special Components (4 files)

### Phase 4: Integration (After Phase 3)
- **Track 12**: Main Page Integration

---

## Critical Design Patterns to Implement

### 1. Message Styling
```tsx
// User Message
<div className="flex w-full items-start gap-2 md:gap-3 justify-end">
  <div className="max-w-[calc(100%-2.5rem)] sm:max-w-[min(fit-content,80%)]">
    <div
      className="wrap-break-word w-fit rounded-2xl px-3 py-2 text-right text-white text-sm"
      style={{ backgroundColor: "#006cff" }}
    >
      {content}
    </div>
  </div>
</div>

// Assistant Message
<div className="flex w-full items-start gap-2 md:gap-3 justify-start">
  <div className="-mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-background ring-1 ring-border">
    <Sparkles size={14} className="text-primary" />
  </div>
  <div className="bg-transparent px-0 py-0 text-left text-sm">
    {content}
  </div>
</div>
```

### 2. Spring Animation (Framer Motion)
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ type: "spring", stiffness: 500, damping: 30, delay: 0.05 }}
>
```

### 3. Message List Spacing
```tsx
<div className="mx-auto flex min-w-0 max-w-4xl flex-col gap-4 px-2 py-4 md:gap-6 md:px-4">
```

### 4. Hover Reveal Actions
```tsx
<div className="flex items-center gap-1 opacity-0 transition-opacity group-hover/message:opacity-100">
```

---

## Verification Checklist

After all tracks complete:

1. **Build succeeds**: `npm run build`
2. **Visual inspection**:
   - [ ] Messages: Blue user (right), transparent assistant (left with avatar)
   - [ ] Spacing: `gap-4 md:gap-6` between messages
   - [ ] Animations: Spring physics on message entry
   - [ ] Header: Sticky, responsive, with all controls
   - [ ] Input: Auto-resize, file attachments, model selector
   - [ ] Sidebar: Collapsible, smooth transitions
   - [ ] Colors: HSL-based warm palette
   - [ ] Border radius: `0.625rem` (10px)

3. **Functionality**:
   - [ ] Message actions (copy, delete) work
   - [ ] Tool messages collapse/expand
   - [ ] File upload works
   - [ ] WebSocket connection works
   - [ ] Mobile responsive

---

## Total File Count: 100+ files

- UI Base: 28 files
- Chat Layout: 3 files
- Messages: 6 files
- Input: 4 files
- Sidebar: 5 files
- Elements: 16 files
- Artifacts: 4 files (optional)
- Special: 4 files
- Styling: 3 files
- Utilities: 2 files
- Integration: 1 file
