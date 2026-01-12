#include <gtk/gtk.h>

static void on_destroy(GtkWidget *widget, gpointer user_data) {
    (void)widget;
    (void)user_data;
    gtk_main_quit();
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    const char *message = "ATENCIÓN\n\nPantalla bloqueada por el profesor.\n\nSigue las instrucciones en clase.";
    if (argc >= 2 && argv[1] && argv[1][0] != '\0') {
        message = argv[1];
    }

    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), "EduControl");
    gtk_window_set_decorated(GTK_WINDOW(window), FALSE);
    gtk_window_set_skip_taskbar_hint(GTK_WINDOW(window), TRUE);
    gtk_window_set_skip_pager_hint(GTK_WINDOW(window), TRUE);
    gtk_window_set_keep_above(GTK_WINDOW(window), TRUE);
    gtk_window_set_accept_focus(GTK_WINDOW(window), TRUE);
    gtk_window_set_focus_on_map(GTK_WINDOW(window), TRUE);
    gtk_window_fullscreen(GTK_WINDOW(window));

    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 24);
    gtk_widget_set_hexpand(box, TRUE);
    gtk_widget_set_vexpand(box, TRUE);
    gtk_container_add(GTK_CONTAINER(window), box);

    GtkWidget *label = gtk_label_new(message);
    gtk_label_set_justify(GTK_LABEL(label), GTK_JUSTIFY_CENTER);
    gtk_label_set_line_wrap(GTK_LABEL(label), TRUE);
    gtk_label_set_xalign(GTK_LABEL(label), 0.5);
    gtk_label_set_yalign(GTK_LABEL(label), 0.5);

    // Tamaño grande sin depender de markup.
    PangoFontDescription *font_desc = pango_font_description_from_string("Sans Bold 48");
    gtk_widget_override_font(label, font_desc);
    pango_font_description_free(font_desc);

    gtk_box_pack_start(GTK_BOX(box), label, TRUE, TRUE, 0);

    // Estilo simple: fondo oscuro y texto claro.
    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(
        provider,
        "window { background: #000000; }\nlabel { color: #ffffff; }\n",
        -1,
        NULL);

    GdkScreen *screen = gdk_screen_get_default();
    if (screen) {
        gtk_style_context_add_provider_for_screen(
            screen,
            GTK_STYLE_PROVIDER(provider),
            GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    }
    g_object_unref(provider);

    g_signal_connect(window, "destroy", G_CALLBACK(on_destroy), NULL);

    gtk_widget_show_all(window);

    // Intento de "grab" de entrada: en Wayland suele fallar; en X11 puede ayudar.
    GdkWindow *gdk_window = gtk_widget_get_window(window);
    if (gdk_window) {
        GdkDisplay *display = gdk_window_get_display(gdk_window);
        GdkSeat *seat = gdk_display_get_default_seat(display);
        if (seat) {
            (void)gdk_seat_grab(
                seat,
                gdk_window,
                GDK_SEAT_CAPABILITY_ALL_POINTING | GDK_SEAT_CAPABILITY_KEYBOARD,
                TRUE,
                NULL,
                NULL,
                NULL,
                NULL);
        }
    }

    gtk_main();
    return 0;
}
