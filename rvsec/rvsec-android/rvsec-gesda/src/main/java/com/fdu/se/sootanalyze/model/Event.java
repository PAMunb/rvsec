package com.fdu.se.sootanalyze.model;

public enum Event {

	CLICK,
	LONG_CLICK,
	SCROLL,
	DRAG,
	HOVER,
	TOUCH,
	FOCUS,
	TEXT_CHANGE,//TODO
	GESTURE,//TODO
	SELECTION;

//Tipos comuns de eventos em views Android:
//
//	Clique (Click): O evento mais comum, ocorre quando o usuário toca em um elemento da interface. É geralmente utilizado em botões, textos clicáveis e outros elementos que requerem uma ação imediata.
//	Clique longo (Long Click): Acionado quando o usuário mantém o dedo pressionado sobre um elemento por um determinado tempo. É utilizado para exibir menus de contexto ou realizar ações mais complexas.
//	Mudança de texto (Text Change): Ocorre quando o conteúdo de um campo de texto (EditText) é alterado. É útil para validar a entrada do usuário, atualizar outros elementos da interface ou realizar buscas em tempo real.
//	Foco (Focus): Acionado quando um elemento ganha ou perde o foco. É utilizado para destacar o elemento ativo e realizar ações específicas quando o usuário navega entre os campos.
//	Seleção (Selection): Ocorre quando um item é selecionado em uma lista (ListView, Spinner). É utilizado para atualizar a interface com base na seleção do usuário.
//	Arrastar (Drag): Permite que o usuário arraste um elemento pela tela. É utilizado em funcionalidades como reordenar itens em uma lista ou mover objetos em um jogo.
//	Gestos (Gesture): Captura gestos mais complexos, como pinçar para ampliar ou girar um elemento.
//	Toque (Touch): Permite capturar eventos de toque mais detalhados, como a posição do toque na tela e a pressão exercida.
//	Como capturar e tratar eventos:

}
