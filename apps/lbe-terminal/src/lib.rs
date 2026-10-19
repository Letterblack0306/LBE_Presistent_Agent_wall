//! LBE terminal client. Presentation and operator control only: the runtime owns
//! identity, authorization, execution, receipts and completion; this crate
//! projects what the bridge reports and sends operator decisions back.
pub mod app;
pub mod bridge;
pub mod model;
pub mod rules;
pub mod text;
pub mod theme;
pub mod update;
pub mod view;
