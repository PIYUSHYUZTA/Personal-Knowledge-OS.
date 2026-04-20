import { cn } from '@/lib/utils'

type SkeletonVariant = 'text' | 'card' | 'avatar' | 'stat-card' | 'custom'

interface SkeletonProps {
  variant?: SkeletonVariant
  className?: string
  lines?: number
  width?: string
  height?: string
}

export default function Skeleton({
  variant = 'text',
  className,
  lines = 1,
  width,
  height,
}: SkeletonProps) {
  if (variant === 'avatar') {
    return (
      <div
        className={cn('skeleton rounded-full', className)}
        style={{ width: width || '40px', height: height || '40px' }}
      />
    )
  }

  if (variant === 'card') {
    return (
      <div className={cn('skeleton rounded-xl p-6 space-y-4', className)} style={{ height: height || '200px' }}>
        <div className="skeleton h-4 w-3/5 rounded" />
        <div className="skeleton h-3 w-4/5 rounded" />
        <div className="skeleton h-3 w-2/5 rounded" />
        <div className="flex-1" />
        <div className="skeleton h-8 w-1/3 rounded-md" />
      </div>
    )
  }

  if (variant === 'stat-card') {
    return (
      <div className={cn('skeleton rounded-xl p-6 flex flex-col', className)} style={{ height: height || '180px' }}>
        <div className="skeleton h-10 w-10 rounded-lg mb-8" />
        <div className="mt-auto space-y-2">
          <div className="skeleton h-3 w-24 rounded" />
          <div className="skeleton h-8 w-16 rounded" />
        </div>
      </div>
    )
  }

  // text variant
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton rounded"
          style={{
            width: width || (i === lines - 1 ? '60%' : '100%'),
            height: height || '14px',
          }}
        />
      ))}
    </div>
  )
}
