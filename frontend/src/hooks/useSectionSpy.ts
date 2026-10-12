import { useEffect, useState } from 'react'

export function useSectionSpy(sectionIds: string[], topOffset = 116) {
  const [activeSection, setActiveSection] = useState(sectionIds[0] ?? '')

  useEffect(() => {
    function updateActiveSection() {
      const sections = sectionIds
        .map((id) => document.getElementById(id))
        .filter((section): section is HTMLElement => section !== null)
      if (!sections.length) return
      const reachedDocumentEnd = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2
      if (reachedDocumentEnd) {
        setActiveSection(sections.at(-1)?.id ?? sections[0].id)
        return
      }
      const current = [...sections]
        .reverse()
        .find((section) => section.getBoundingClientRect().top <= topOffset)
      setActiveSection(current?.id ?? sections[0].id)
    }

    updateActiveSection()
    window.addEventListener('scroll', updateActiveSection, { passive: true })
    window.addEventListener('resize', updateActiveSection)
    return () => {
      window.removeEventListener('scroll', updateActiveSection)
      window.removeEventListener('resize', updateActiveSection)
    }
  }, [sectionIds, topOffset])

  return activeSection
}
