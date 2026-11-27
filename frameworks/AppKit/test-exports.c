/* Link-only fixture. The declarations below are never used to call AppKit. */
extern void NSBeep(void);
extern const double NSFontWeightSemibold;
extern void NSRectFill(void);
extern void NSRectFillUsingOperation(void);
extern const void *NSWorkspaceAccessibilityDisplayOptionsDidChangeNotification;
extern const void *NSAppearanceNameAqua;
extern const void *NSAppearanceNameDarkAqua;
extern const void *NSAppearanceNameAccessibilityHighContrastAqua;
extern const void *NSAppearanceNameAccessibilityHighContrastDarkAqua;

const void *appkit_exports[] = {
    (const void *)NSBeep,
    &NSFontWeightSemibold,
    (const void *)NSRectFill,
    (const void *)NSRectFillUsingOperation,
    &NSWorkspaceAccessibilityDisplayOptionsDidChangeNotification,
    &NSAppearanceNameAqua,
    &NSAppearanceNameDarkAqua,
    &NSAppearanceNameAccessibilityHighContrastAqua,
    &NSAppearanceNameAccessibilityHighContrastDarkAqua,
};

int main(void) {
    return appkit_exports[0] == 0;
}
