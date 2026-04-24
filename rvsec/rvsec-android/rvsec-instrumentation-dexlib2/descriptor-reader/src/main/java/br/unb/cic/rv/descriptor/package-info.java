/**
 * POJO model for the JSON descriptor emitted by patched JavaMOP
 * ({@code javamop --emit-descriptor}).
 *
 * <p>This module is pure-POJO per design decision D1: it carries no
 * pointcut parsing, no DEX logic, and depends only on Jackson + slf4j.
 * Consumers ({@code pointcut-engine}, {@code advice-emitter},
 * {@code dex-mutator}) receive a strongly-typed tree they can query
 * without re-reading the raw JSON.
 */
package br.unb.cic.rv.descriptor;
