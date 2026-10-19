//! Semantic style slots and glyph sets. Widgets ask for a slot, never a colour,
//! so NO_COLOR, ASCII and no-motion modes change one place.
use ratatui::style::{Color, Modifier, Style};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Display {
    pub color: bool,
    pub unicode: bool,
    pub motion: bool,
}

impl Display {
    /// Explicit LBE settings win; a non-empty `NO_COLOR` turns colour off.
    pub fn from_env(get: impl Fn(&str) -> Option<String>) -> Display {
        let on = |k: &str| get(k).map(|v| !v.is_empty() && v != "0").unwrap_or(false);
        Display {
            color: !on("NO_COLOR"),
            unicode: !on("LBE_ASCII"),
            motion: !on("LBE_NO_MOTION"),
        }
    }
}

#[derive(Clone, Copy)]
pub struct Theme {
    pub d: Display,
}

const FG: Color = Color::Rgb(0xe9, 0xe9, 0xef);
const MUTED: Color = Color::Rgb(0x8e, 0x8e, 0x93);
const ACCENT: Color = Color::Rgb(0xef, 0x4b, 0x4b);
const OK: Color = Color::Rgb(0x4a, 0xde, 0x80);
const WARN: Color = Color::Rgb(0xe5, 0xb5, 0x67);
const SEL_BG: Color = Color::Rgb(0x1c, 0x1d, 0x29);
const LINE: Color = Color::Rgb(0x2a, 0x2a, 0x2d);

impl Theme {
    pub fn new(d: Display) -> Theme {
        Theme { d }
    }

    fn c(&self, color: Color) -> Style {
        if self.d.color {
            Style::default().fg(color)
        } else {
            Style::default()
        }
    }

    pub fn text(&self) -> Style {
        self.c(FG)
    }
    pub fn muted(&self) -> Style {
        self.c(MUTED)
    }
    pub fn label(&self) -> Style {
        self.c(MUTED).add_modifier(Modifier::BOLD)
    }
    pub fn strong(&self) -> Style {
        self.c(FG).add_modifier(Modifier::BOLD)
    }
    pub fn accent(&self) -> Style {
        self.c(ACCENT).add_modifier(Modifier::BOLD)
    }
    pub fn ok(&self) -> Style {
        self.c(OK)
    }
    pub fn warn(&self) -> Style {
        self.c(WARN)
    }
    pub fn err(&self) -> Style {
        self.c(ACCENT)
    }
    pub fn rule(&self) -> Style {
        self.c(LINE)
    }
    /// Selected row: background in colour mode, reverse video in monochrome.
    pub fn selected(&self) -> Style {
        if self.d.color {
            Style::default().bg(SEL_BG)
        } else {
            Style::default().add_modifier(Modifier::REVERSED)
        }
    }

    pub fn g(&self) -> Glyphs {
        if self.d.unicode {
            Glyphs {
                rule: "─",
                cursor: "▸",
                ok: "✓",
                dot: "·",
                busy: "●",
                arrow: "→",
                fill: "█",
                empty: "░",
                bar_l: "▕",
                bar_r: "▏",
                mark: ["[", "┃", "]"],
                block: "■",
                failed: "✗",
                info: "i",
                needs: "?",
                partial: "~",
                prompt: "❯",
                heavy: "━",
                off: "○",
            }
        } else {
            Glyphs {
                rule: "-",
                cursor: ">",
                ok: "v",
                dot: ".",
                busy: "*",
                arrow: "->",
                fill: "#",
                empty: ".",
                bar_l: "[",
                bar_r: "]",
                mark: ["[", "|", "]"],
                block: "x",
                failed: "X",
                info: "i",
                needs: "?",
                partial: "~",
                prompt: ">",
                heavy: "=",
                off: "o",
            }
        }
    }
}

#[derive(Clone, Copy)]
pub struct Glyphs {
    pub rule: &'static str,
    pub cursor: &'static str,
    pub ok: &'static str,
    pub dot: &'static str,
    pub busy: &'static str,
    pub arrow: &'static str,
    pub fill: &'static str,
    pub empty: &'static str,
    pub bar_l: &'static str,
    pub bar_r: &'static str,
    pub mark: [&'static str; 3],
    pub block: &'static str,
    pub failed: &'static str,
    pub info: &'static str,
    pub needs: &'static str,
    pub partial: &'static str,
    pub prompt: &'static str,
    pub heavy: &'static str,
    pub off: &'static str,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn env(pairs: &'static [(&'static str, &'static str)]) -> impl Fn(&str) -> Option<String> {
        move |k| {
            pairs
                .iter()
                .find(|(n, _)| *n == k)
                .map(|(_, v)| v.to_string())
        }
    }

    #[test]
    fn no_color_only_removes_colour() {
        let d = Display::from_env(env(&[("NO_COLOR", "1")]));
        assert!(!d.color && d.unicode && d.motion);
        let t = Theme::new(d);
        assert_eq!(t.text().fg, None);
        assert!(t.strong().add_modifier.contains(Modifier::BOLD));
        assert!(t.selected().add_modifier.contains(Modifier::REVERSED));
    }

    #[test]
    fn empty_no_color_is_ignored() {
        assert!(Display::from_env(env(&[("NO_COLOR", "")])).color);
    }

    #[test]
    fn ascii_mode_has_only_ascii_glyphs() {
        let g = Theme::new(Display::from_env(env(&[("LBE_ASCII", "1")]))).g();
        for s in [
            g.rule, g.cursor, g.ok, g.dot, g.busy, g.arrow, g.fill, g.empty, g.bar_l, g.bar_r,
            g.mark[1], g.block, g.failed, g.info, g.needs, g.partial, g.prompt, g.heavy, g.off,
        ] {
            assert!(s.is_ascii(), "{s}");
        }
    }
}
