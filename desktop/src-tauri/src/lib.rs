mod types;
mod commands;

use types::AppState;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState::new())
        .invoke_handler(tauri::generate_handler![
            commands::submit_task,
            commands::get_task_status,
            commands::get_task_result,
            commands::list_tasks,
            commands::delete_task,
            commands::update_config,
            commands::get_config,
            commands::check_server_health,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
