# Vintage Icon System

## Overview
Custom SVG icon system with a vintage/retro design instead of simple emoji. The icons are designed with smooth gradients, subtle animations, and refined hover effects.

## Design Philosophy

### Vintage Style Features
- **Linear Gradients**: Smooth color transitions
- **Soft Shadows**: Adds vintage depth
- **Rounded Corners**: Modern rounded shapes
- **Subtle Animations**: Gentle motion, not flashy
- **Fill Opacity**: Light translucent fills for depth

## Available Icons

### Navigation Icons
- `HomeIcon` - Dashboard/Home (Yellow gradient)
- `BookIcon` - Classrooms (Yellow gradient)
- `CalendarIcon` - Calendar view (Pink gradient)
- `SettingsIcon` - Settings (Slate gradient)

### Feature Icons
- `UsersIcon` - Students/People (Blue gradient)
- `PackageIcon` - Teaching packs (Purple gradient)
- `ActivityIcon` - Activity feed (Green gradient)
- `BellIcon` - Notifications (Yellow gradient)
- `SearchIcon` - Search (Slate gradient)

### Action Icons
- `PlusIcon` - Add/Create (White gradient)
- `UploadIcon` - Upload files (Blue gradient)
- `ChartIcon` - Reports/Analytics (Purple gradient)
- `SparklesIcon` - Highlights/Special (Gold gradient)

### View Mode Icons
- `GridIcon` - Grid view (Slate gradient)
- `ListIcon` - List view (Slate gradient)

### Status Icons
- `CheckCircleIcon` - Success (Green gradient)
- `InfoCircleIcon` - Information (Blue gradient)
- `WarningIcon` - Warning (Yellow gradient)
- `ErrorIcon` - Error (Red gradient)

## Color Palette

### Gradients Used
```css
Yellow:  #eab308 -> #ca8a04
Blue:   #3b82f6 -> #1d4ed8
Purple: #8b5cf6 -> #6d28d9
Green:  #10b981 -> #059669
Pink:   #ec4899 -> #db2777
Slate:  #64748b -> #475569
Gold:   #fbbf24 -> #eab308
Red:    #ef4444 -> #dc2626
```

## Animation Classes

### Available Animations
```css
.icon-float      // Floating effect (3s infinite)
.icon-pulse      // Pulsing effect (2s infinite)
.icon-spin       // Spinning effect (20s infinite)
.icon-bounce     // Bouncing effect (1s infinite)
```

### Hover Effects
```css
.icon-hover-scale   // Scale up on hover
.icon-hover-rotate  // Rotate on hover
```

### Icon Containers
```css
.icon-container-yellow   // Yellow gradient background
.icon-container-blue    // Blue gradient background
.icon-container-purple  // Purple gradient background
.icon-container-green   // Green gradient background
.icon-container-pink    // Pink gradient background
```

## Usage Examples

### Basic Icon
```tsx
import { BookIcon } from './icons/Icons';

<BookIcon size={24} />
```

### Icon with Animation
```tsx
<div className="icon-float">
  <SparklesIcon size={80} />
</div>
```

### Icon in Container
```tsx
<div className="p-2 icon-container-yellow rounded-lg icon-hover-scale">
  <BookIcon size={28} />
</div>
```

### Icon with Custom Classes
```tsx
<SearchIcon size={20} className="text-stone-600" />
```

## Design Principles

1. **Consistent Sizing**:
   - Small: 16-20px (List items, inline)
   - Medium: 24-32px (Buttons, cards)
   - Large: 48-80px (Headers, empty states)

2. **Stroke Width**: 2-2.5px for clear linework

3. **Fill Opacity**: 0.1-0.2 for subtle background fills

4. **Gradient Direction**:
   - Linear: 0% to 100% (top-left to bottom-right)
   - Consistent across similar icons

5. **SVG Optimization**:
   - Clean paths
   - Minimal nodes
   - Reusable defs

## Advantages over Emoji

### Why Custom SVG Icons...

- **Consistent Design**: Same look across platforms and browsers
- **Scalable**: Vector format, no pixelation when zooming
- **Customizable**: Easy to change color, size, animation
- **Professional**: Looks more polished than emoji
- **Lightweight**: No heavy icon library needed
- **Brand Matching**: Fits the app color scheme
- **Vintage Aesthetic**: Retro/vintage style

### Performance
- No external dependencies
- Inline SVG = no extra HTTP requests
- Small file size (~1-2KB per icon)
- Fast rendering

## Future Enhancements

Potential additions:
- [ ] More icons (video, document, folder, etc.)
- [ ] Dark mode variants
- [ ] Animated icons (lottie-style)
- [ ] Icon picker component
- [ ] More gradient variations
- [ ] Micro-interactions on click

## Notes

- Icons inherit color from parent when no gradient is set
- Use the `className` prop to override styles
- All icons support the `size` prop (default: 24px)
- Animations are defined in `icon-animations.css`

## Customization

### Creating New Icons
1. Design in Figma/Illustrator
2. Export as SVG
3. Clean up code
4. Add gradient definitions
5. Add to Icons.tsx
6. Export from index.ts

### Gradient Template
```tsx
<defs>
  <linearGradient id="iconGradient" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stopColor="#color1" />
    <stop offset="100%" stopColor="#color2" />
  </linearGradient>
</defs>
```

---

Created with care for Teaching Pack Generator.
Vintage design meets modern functionality.
