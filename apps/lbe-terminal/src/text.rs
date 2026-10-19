//! Terminal-cell text helpers. Everything shown from a provider, file or tool is
//! untrusted: control sequences are stripped before it reaches a widget.
use unicode_segmentation::UnicodeSegmentation;
use unicode_width::UnicodeWidthStr;

/// Remove escape sequences and control characters (keeps `\n`, turns `\t` into spaces).
pub fn sanitize(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    let mut chars = input.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '\x1b' => match chars.peek() {
                // CSI: ESC [ ... final byte 0x40..=0x7e
                Some('[') => {
                    chars.next();
                    for n in chars.by_ref() {
                        if ('\x40'..='\x7e').contains(&n) {
                            break;
                        }
                    }
                }
                // OSC: ESC ] ... BEL or ESC \
                Some(']') => {
                    chars.next();
                    while let Some(n) = chars.next() {
                        if n == '\x07' {
                            break;
                        }
                        if n == '\x1b' {
                            chars.next();
                            break;
                        }
                    }
                }
                _ => {
                    chars.next();
                }
            },
            '\t' => out.push_str("    "),
            '\r' => {}
            c if c == '\n' || !c.is_control() => out.push(c),
            _ => {}
        }
    }
    out
}

pub fn width(s: &str) -> usize {
    UnicodeWidthStr::width(s)
}

/// Clip to `max` terminal cells on a grapheme boundary; adds `…` (or `~` in ASCII) when cut.
pub fn clip(s: &str, max: usize, ascii: bool) -> String {
    if width(s) <= max {
        return s.to_string();
    }
    let ell = if ascii { "~" } else { "…" };
    if max == 0 {
        return String::new();
    }
    let mut out = String::new();
    let mut used = 0;
    for g in s.graphemes(true) {
        let w = width(g);
        if used + w + 1 > max {
            break;
        }
        out.push_str(g);
        used += w;
    }
    out.push_str(ell);
    out
}

/// Clip from the left (keeps the tail of a path) to `max` cells.
pub fn clip_left(s: &str, max: usize, ascii: bool) -> String {
    if width(s) <= max {
        return s.to_string();
    }
    let ell = if ascii { "~" } else { "…" };
    if max == 0 {
        return String::new();
    }
    let mut kept: Vec<&str> = Vec::new();
    let mut used = 0;
    for g in s.graphemes(true).rev() {
        let w = width(g);
        if used + w + 1 > max {
            break;
        }
        kept.push(g);
        used += w;
    }
    kept.reverse();
    format!("{ell}{}", kept.concat())
}

/// Pad with spaces (or clip) to exactly `n` cells.
pub fn pad(s: &str, n: usize) -> String {
    let clipped = clip(s, n, false);
    let w = width(&clipped);
    format!("{clipped}{}", " ".repeat(n.saturating_sub(w)))
}

/// Word-wrap to `max` cells; hard-breaks words longer than a line.
pub fn wrap(s: &str, max: usize) -> Vec<String> {
    let max = max.max(1);
    let mut lines = Vec::new();
    for raw in s.split('\n') {
        let mut line = String::new();
        let mut line_w = 0;
        for word in raw.split(' ') {
            let ww = width(word);
            if ww > max {
                if !line.is_empty() {
                    lines.push(std::mem::take(&mut line));
                }
                let mut chunk = String::new();
                let mut cw = 0;
                for g in word.graphemes(true) {
                    let gw = width(g);
                    if cw + gw > max {
                        lines.push(std::mem::take(&mut chunk));
                        cw = 0;
                    }
                    chunk.push_str(g);
                    cw += gw;
                }
                line = chunk;
                line_w = cw;
                continue;
            }
            let extra = if line.is_empty() { 0 } else { 1 };
            if line_w + extra + ww > max {
                lines.push(std::mem::take(&mut line));
                line_w = 0;
            }
            if !line.is_empty() {
                line.push(' ');
                line_w += 1;
            }
            line.push_str(word);
            line_w += ww;
        }
        lines.push(line);
    }
    lines
}

/// Replies arrive as markdown; the transcript shows plain text.
pub fn plain_markdown(s: &str) -> String {
    s.lines()
        .map(|l| {
            let t = l.trim_start_matches('#').trim_start();
            t.replace("**", "").replace('`', "")
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Remove the last grapheme (backspace).
pub fn pop_grapheme(s: &mut String) {
    if let Some((i, _)) = s.grapheme_indices(true).next_back() {
        s.truncate(i);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanitize_strips_escape_sequences_and_controls() {
        assert_eq!(
            sanitize("a\x1b[31mred\x1b[0m b\x1b]0;title\x07c\x07d"),
            "ared bcd"
        );
        assert_eq!(sanitize("x\r\ny\tz"), "x\ny    z");
    }

    #[test]
    fn clip_counts_cells_not_chars() {
        assert_eq!(clip("日本語テキスト", 7, false), "日本語…");
        assert_eq!(width(&clip("日本語テキスト", 7, false)), 7);
        assert_eq!(clip("abcdef", 4, true), "abc~");
        assert_eq!(clip("abc", 4, false), "abc");
    }

    #[test]
    fn clip_left_keeps_the_tail() {
        assert_eq!(clip_left("src/very/long/cli.py", 10, false), "…ng/cli.py");
        assert_eq!(clip_left("cli.py", 10, false), "cli.py");
        assert_eq!(clip_left("abcdef", 4, true), "~def");
    }

    #[test]
    fn clip_never_splits_a_grapheme() {
        let s = "e\u{301}e\u{301}e\u{301}e\u{301}";
        let c = clip(s, 3, false);
        assert!(c.starts_with("e\u{301}e\u{301}"), "{c:?}");
    }

    #[test]
    fn wrap_breaks_long_words_and_keeps_newlines() {
        assert_eq!(wrap("aa bb cc", 5), vec!["aa bb", "cc"]);
        assert_eq!(wrap("abcdefgh", 3), vec!["abc", "def", "gh"]);
        assert_eq!(wrap("a\nb", 5), vec!["a", "b"]);
    }

    #[test]
    fn pad_is_exact_width() {
        assert_eq!(width(&pad("日本", 6)), 6);
        assert_eq!(width(&pad("toolongvalue", 5)), 5);
    }

    #[test]
    fn markdown_is_flattened() {
        assert_eq!(
            plain_markdown("# Title\n**bold** `code`"),
            "Title\nbold code"
        );
    }

    #[test]
    fn pop_grapheme_removes_whole_cluster() {
        let mut s = String::from("ae\u{301}");
        pop_grapheme(&mut s);
        assert_eq!(s, "a");
    }
}
