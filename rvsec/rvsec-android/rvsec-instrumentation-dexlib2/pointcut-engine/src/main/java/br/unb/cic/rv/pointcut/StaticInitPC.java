package br.unb.cic.rv.pointcut;

/**
 * {@code staticinitialization(<typePattern>)} — matches class initializer
 * ({@code <clinit>}) of types matching the pattern.
 *
 * <p>A type pattern ending in {@code +} (e.g. {@code T+}) means "T and every
 * declared subtype"; the matcher expands this against the current APK class
 * hierarchy (and android.jar, for framework subtypes).
 */
public record StaticInitPC(String typePattern) implements PointcutExpression {
}
