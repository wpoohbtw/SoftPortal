import { useCallback, useEffect, useMemo, useRef } from 'react'
import gsap from 'gsap'
import './TargetCursor.css'

type TargetCursorProps = {
  targetSelector?: string
  spinDuration?: number
  hideDefaultCursor?: boolean
  hoverDuration?: number
  parallaxOn?: boolean
}

type CursorPoint = {
  x: number
  y: number
}

const getContainingBlock = (element: HTMLElement | null): HTMLElement | null => {
  let node = element?.parentElement ?? null
  while (node && node !== document.documentElement) {
    const style = getComputedStyle(node)
    if (
      style.transform !== 'none' ||
      style.perspective !== 'none' ||
      style.filter !== 'none' ||
      style.willChange.includes('transform') ||
      style.willChange.includes('perspective') ||
      style.willChange.includes('filter') ||
      /paint|layout|strict|content/.test(style.contain)
    ) {
      return node
    }
    node = node.parentElement
  }
  return null
}

const getContainingBlockOffset = (block: HTMLElement | null): CursorPoint => {
  if (!block) return { x: 0, y: 0 }
  const rect = block.getBoundingClientRect()
  return { x: rect.left + block.clientLeft, y: rect.top + block.clientTop }
}

function isMobileDevice(): boolean {
  const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0
  const isSmallScreen = window.innerWidth <= 768
  const userAgent = navigator.userAgent || navigator.vendor || ''
  const isMobileUserAgent = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent.toLowerCase())
  return (hasTouchScreen && isSmallScreen) || isMobileUserAgent
}

export default function TargetCursor({
  targetSelector = '.cursor-target',
  spinDuration = 2,
  hideDefaultCursor = true,
  hoverDuration = 0.2,
  parallaxOn = true,
}: TargetCursorProps) {
  const cursorRef = useRef<HTMLDivElement | null>(null)
  const cornersRef = useRef<NodeListOf<HTMLDivElement> | null>(null)
  const spinTl = useRef<gsap.core.Timeline | null>(null)
  const dotRef = useRef<HTMLDivElement | null>(null)
  const containingBlockRef = useRef<HTMLElement | null>(null)
  const targetCornerPositionsRef = useRef<CursorPoint[] | null>(null)
  const tickerFnRef = useRef<(() => void) | null>(null)
  const activeStrengthRef = useRef({ current: 0 })

  const isMobile = useMemo(() => (typeof window === 'undefined' ? true : isMobileDevice()), [])
  const constants = useMemo(() => ({ borderWidth: 8, cornerSize: 12 }), [])

  const moveCursor = useCallback((x: number, y: number) => {
    if (!cursorRef.current) return
    const { x: offsetX, y: offsetY } = getContainingBlockOffset(containingBlockRef.current)
    gsap.to(cursorRef.current, {
      x: x - offsetX,
      y: y - offsetY,
      duration: 0.1,
      ease: 'power3.out',
    })
  }, [])

  useEffect(() => {
    if (isMobile || !cursorRef.current) return undefined

    const originalCursor = document.body.style.cursor
    if (hideDefaultCursor) {
      document.body.style.cursor = 'none'
    }

    const cursor = cursorRef.current
    cornersRef.current = cursor.querySelectorAll<HTMLDivElement>('.target-cursor-corner')
    containingBlockRef.current = getContainingBlock(cursor)
    const getOffset = () => getContainingBlockOffset(containingBlockRef.current)

    let activeTarget: HTMLElement | null = null
    let currentLeaveHandler: (() => void) | null = null
    let resumeTimeout: number | null = null

    const cleanupTarget = (target: HTMLElement) => {
      if (currentLeaveHandler) {
        target.removeEventListener('mouseleave', currentLeaveHandler)
      }
      currentLeaveHandler = null
    }

    const initialOffset = getOffset()
    gsap.set(cursor, {
      xPercent: -50,
      yPercent: -50,
      x: window.innerWidth / 2 - initialOffset.x,
      y: window.innerHeight / 2 - initialOffset.y,
    })

    const createSpinTimeline = () => {
      spinTl.current?.kill()
      spinTl.current = gsap.timeline({ repeat: -1 }).to(cursor, { rotation: '+=360', duration: spinDuration, ease: 'none' })
    }

    createSpinTimeline()

    const tickerFn = () => {
      if (!targetCornerPositionsRef.current || !cursorRef.current || !cornersRef.current) return
      const strength = activeStrengthRef.current.current
      if (strength === 0) return

      const cursorX = Number(gsap.getProperty(cursorRef.current, 'x'))
      const cursorY = Number(gsap.getProperty(cursorRef.current, 'y'))

      Array.from(cornersRef.current).forEach((corner, index) => {
        const currentX = Number(gsap.getProperty(corner, 'x'))
        const currentY = Number(gsap.getProperty(corner, 'y'))
        const targetPosition = targetCornerPositionsRef.current?.[index]
        if (!targetPosition) return

        const targetX = targetPosition.x - cursorX
        const targetY = targetPosition.y - cursorY
        const finalX = currentX + (targetX - currentX) * strength
        const finalY = currentY + (targetY - currentY) * strength
        const duration = strength >= 0.99 ? (parallaxOn ? 0.2 : 0) : 0.05

        gsap.to(corner, {
          x: finalX,
          y: finalY,
          duration,
          ease: duration === 0 ? 'none' : 'power1.out',
          overwrite: 'auto',
        })
      })
    }

    tickerFnRef.current = tickerFn

    const moveHandler = (event: MouseEvent) => moveCursor(event.clientX, event.clientY)
    window.addEventListener('mousemove', moveHandler)

    const scrollHandler = () => {
      if (!activeTarget || !cursorRef.current) return
      const { x: offsetX, y: offsetY } = getOffset()
      const mouseX = Number(gsap.getProperty(cursorRef.current, 'x')) + offsetX
      const mouseY = Number(gsap.getProperty(cursorRef.current, 'y')) + offsetY
      const elementUnderMouse = document.elementFromPoint(mouseX, mouseY)
      const isStillOverTarget =
        elementUnderMouse && (elementUnderMouse === activeTarget || elementUnderMouse.closest(targetSelector) === activeTarget)
      if (!isStillOverTarget && currentLeaveHandler) currentLeaveHandler()
    }
    window.addEventListener('scroll', scrollHandler, { passive: true })

    const mouseDownHandler = () => {
      if (!dotRef.current) return
      gsap.to(dotRef.current, { scale: 0.7, duration: 0.3 })
      gsap.to(cursor, { scale: 0.9, duration: 0.2 })
    }

    const mouseUpHandler = () => {
      if (!dotRef.current) return
      gsap.to(dotRef.current, { scale: 1, duration: 0.3 })
      gsap.to(cursor, { scale: 1, duration: 0.2 })
    }

    window.addEventListener('mousedown', mouseDownHandler)
    window.addEventListener('mouseup', mouseUpHandler)

    const enterHandler = (event: MouseEvent) => {
      const directTarget = event.target
      if (!(directTarget instanceof Element)) return

      const target = directTarget.closest<HTMLElement>(targetSelector)
      if (!target || !cursorRef.current || !cornersRef.current) return
      if (activeTarget === target) return
      if (activeTarget) cleanupTarget(activeTarget)
      if (resumeTimeout) {
        window.clearTimeout(resumeTimeout)
        resumeTimeout = null
      }

      activeTarget = target
      const corners = Array.from(cornersRef.current)
      corners.forEach((corner) => gsap.killTweensOf(corner))

      gsap.killTweensOf(cursorRef.current, 'rotation')
      spinTl.current?.pause()
      gsap.set(cursorRef.current, { rotation: 0 })

      const rect = target.getBoundingClientRect()
      const { borderWidth, cornerSize } = constants
      const { x: offsetX, y: offsetY } = getOffset()
      const cursorX = Number(gsap.getProperty(cursorRef.current, 'x'))
      const cursorY = Number(gsap.getProperty(cursorRef.current, 'y'))

      targetCornerPositionsRef.current = [
        { x: rect.left - borderWidth - offsetX, y: rect.top - borderWidth - offsetY },
        { x: rect.right + borderWidth - cornerSize - offsetX, y: rect.top - borderWidth - offsetY },
        { x: rect.right + borderWidth - cornerSize - offsetX, y: rect.bottom + borderWidth - cornerSize - offsetY },
        { x: rect.left - borderWidth - offsetX, y: rect.bottom + borderWidth - cornerSize - offsetY },
      ]

      gsap.ticker.add(tickerFn)
      gsap.to(activeStrengthRef.current, {
        current: 1,
        duration: hoverDuration,
        ease: 'power2.out',
      })

      corners.forEach((corner, index) => {
        const targetPosition = targetCornerPositionsRef.current?.[index]
        if (!targetPosition) return
        gsap.to(corner, {
          x: targetPosition.x - cursorX,
          y: targetPosition.y - cursorY,
          duration: 0.2,
          ease: 'power2.out',
        })
      })

      const leaveHandler = () => {
        gsap.ticker.remove(tickerFn)
        targetCornerPositionsRef.current = null
        gsap.set(activeStrengthRef.current, { current: 0, overwrite: true })
        activeTarget = null

        if (cornersRef.current) {
          const positions = [
            { x: -cornerSize * 1.5, y: -cornerSize * 1.5 },
            { x: cornerSize * 0.5, y: -cornerSize * 1.5 },
            { x: cornerSize * 0.5, y: cornerSize * 0.5 },
            { x: -cornerSize * 1.5, y: cornerSize * 0.5 },
          ]
          const timeline = gsap.timeline()
          Array.from(cornersRef.current).forEach((corner, index) => {
            timeline.to(
              corner,
              {
                x: positions[index].x,
                y: positions[index].y,
                duration: 0.3,
                ease: 'power3.out',
              },
              0,
            )
          })
        }

        resumeTimeout = window.setTimeout(() => {
          if (!activeTarget && cursorRef.current && spinTl.current) {
            const currentRotation = Number(gsap.getProperty(cursorRef.current, 'rotation'))
            const normalizedRotation = currentRotation % 360
            spinTl.current.kill()
            spinTl.current = gsap
              .timeline({ repeat: -1 })
              .to(cursorRef.current, { rotation: '+=360', duration: spinDuration, ease: 'none' })
            gsap.to(cursorRef.current, {
              rotation: normalizedRotation + 360,
              duration: spinDuration * (1 - normalizedRotation / 360),
              ease: 'none',
              onComplete: () => {
                spinTl.current?.restart()
              },
            })
          }
          resumeTimeout = null
        }, 50)

        cleanupTarget(target)
      }

      currentLeaveHandler = leaveHandler
      target.addEventListener('mouseleave', leaveHandler)
    }

    window.addEventListener('mouseover', enterHandler, { passive: true })

    const resizeHandler = () => {
      containingBlockRef.current = getContainingBlock(cursor)
    }
    window.addEventListener('resize', resizeHandler)

    return () => {
      if (tickerFnRef.current) gsap.ticker.remove(tickerFnRef.current)
      window.removeEventListener('mousemove', moveHandler)
      window.removeEventListener('mouseover', enterHandler)
      window.removeEventListener('scroll', scrollHandler)
      window.removeEventListener('resize', resizeHandler)
      window.removeEventListener('mousedown', mouseDownHandler)
      window.removeEventListener('mouseup', mouseUpHandler)
      if (activeTarget) cleanupTarget(activeTarget)
      if (resumeTimeout) window.clearTimeout(resumeTimeout)
      spinTl.current?.kill()
      document.body.style.cursor = originalCursor
      targetCornerPositionsRef.current = null
      activeStrengthRef.current.current = 0
    }
  }, [targetSelector, spinDuration, moveCursor, constants, hideDefaultCursor, isMobile, hoverDuration, parallaxOn])

  useEffect(() => {
    if (isMobile || !cursorRef.current || !spinTl.current || !spinTl.current.isActive()) return
    spinTl.current.kill()
    spinTl.current = gsap.timeline({ repeat: -1 }).to(cursorRef.current, { rotation: '+=360', duration: spinDuration, ease: 'none' })
  }, [spinDuration, isMobile])

  if (isMobile) return null

  return (
    <div ref={cursorRef} className="target-cursor-wrapper">
      <div ref={dotRef} className="target-cursor-dot" />
      <div className="target-cursor-corner corner-tl" />
      <div className="target-cursor-corner corner-tr" />
      <div className="target-cursor-corner corner-br" />
      <div className="target-cursor-corner corner-bl" />
    </div>
  )
}
